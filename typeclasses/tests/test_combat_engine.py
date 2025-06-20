from unittest.mock import MagicMock, patch, call
import unittest
from evennia.utils.test_resources import EvenniaTest

from combat.engine import CombatEngine
from combat.combat_actions import Action, CombatResult, AttackAction
from utils.currency import from_copper, to_copper
from combat.combat_utils import get_condition_msg
from commands import npc_builder
from django.conf import settings
from django.test import override_settings


class KillAction(Action):
    def resolve(self):
        self.target.hp = 0
        return CombatResult(self.actor, self.target, "boom")


class Dummy:
    def __init__(self, hp=10, init=0):
        self.hp = hp
        self.location = MagicMock()
        self.traits = MagicMock()
        self.traits.get.return_value = MagicMock(value=init)
        self.traits.health = MagicMock(value=self.hp, max=self.hp)
        self.db = type(
            "DB",
            (),
            {
                "temp_bonuses": {},
                "experience": 0,
                "tnl": settings.XP_TO_LEVEL(1),
                "level": 1,
            },
        )()
        self.on_enter_combat = MagicMock()
        self.on_exit_combat = MagicMock()
        self.msg = MagicMock()

    def at_damage(self, attacker, amount, damage_type=None):
        self.hp = max(self.hp - amount, 0)
        if hasattr(self.traits, "health"):
            self.traits.health.value = self.hp
        return amount


class UnsavedDummy(Dummy):
    class FakeDB:
        def __setattr__(self, name, value):
            raise AttributeError("unsaved object")

    def __init__(self, hp=10, init=0):
        super().__init__(hp, init)
        self.pk = None
        self.db = self.FakeDB()


class NoHealth:
    def __init__(self):
        self.location = MagicMock()
        self.traits = MagicMock()
        self.db = type(
            "DB",
            (),
            {
                "temp_bonuses": {},
                "combat_target": None,
                "experience": 0,
                "tnl": settings.XP_TO_LEVEL(1),
                "level": 1,
            },
        )()
        self.on_enter_combat = MagicMock()
        self.on_exit_combat = MagicMock()
        self.msg = MagicMock()


class TestCombatEngine(unittest.TestCase):
    def test_enter_and_exit_callbacks(self):
        a = Dummy()
        b = Dummy()
        with patch('world.system.state_manager.apply_regen'):
            engine = CombatEngine([a, b], round_time=0)
            a.on_enter_combat.assert_called()
            b.on_enter_combat.assert_called()
            engine.queue_action(a, KillAction(a, b))
            engine.start_round()
            engine.process_round()
            b.on_exit_combat.assert_called()

    def test_initiative_and_regen(self):
        a = Dummy(init=10)
        b = Dummy(init=1)
        engine = CombatEngine([a, b], round_time=0)
        with patch('world.system.state_manager.apply_regen') as mock_regen, patch('random.randint', return_value=0):
            engine.start_round()
            self.assertEqual(engine.queue[0].actor, a)
            self.assertEqual(mock_regen.call_count, 2)

    def test_aggro_tracking(self):
        a = Dummy()
        b = Dummy()
        with patch('world.system.state_manager.apply_regen'):
            engine = CombatEngine([a, b], round_time=0)
            engine.queue_action(a, KillAction(a, b))
            engine.start_round()
            engine.process_round()
            self.assertIn(a, engine.aggro.get(b, {}))

    def test_solo_gain_awards_exp(self):
        attacker = Dummy()
        attacker.db.experience = 0
        victim = Dummy()
        victim.db.exp_reward = 10
        with patch('world.system.state_manager.apply_regen'), \
             patch('world.system.state_manager.check_level_up'), \
             patch.object(attacker, 'msg') as mock_msg:
            engine = CombatEngine([attacker, victim], round_time=0)
            engine.queue_action(attacker, KillAction(attacker, victim))
            engine.start_round()
            engine.process_round()
            self.assertEqual(attacker.db.experience, 10)
            mock_msg.assert_called()

    def test_group_gain_splits_exp(self):
        a = Dummy()
        b = Dummy()
        for obj in (a, b):
            obj.db.experience = 0
        victim = Dummy()
        victim.db.exp_reward = 9
        with patch('world.system.state_manager.apply_regen'), \
             patch('world.system.state_manager.check_level_up'), \
             patch.object(a, 'msg') as msg_a, patch.object(b, 'msg') as msg_b:
            engine = CombatEngine([a, b, victim], round_time=0)
            engine.aggro[victim] = {a: 1, b: 1}
            engine.queue_action(a, KillAction(a, victim))
            engine.start_round()
            engine.process_round()
            self.assertEqual(a.db.experience, 4)
            self.assertEqual(b.db.experience, 4)
            msg_a.assert_called()
            msg_b.assert_called()

    def test_group_gain_minimum_share(self):
        members = [Dummy() for _ in range(20)]
        for m in members:
            m.db.experience = 0
        victim = Dummy()
        victim.db.exp_reward = 100
        with patch('world.system.state_manager.apply_regen'), \
             patch('world.system.state_manager.check_level_up'):
            engine = CombatEngine(members + [victim], round_time=0)
            engine.aggro[victim] = {m: 1 for m in members}
            engine.queue_action(members[0], KillAction(members[0], victim))
            engine.start_round()
            engine.process_round()
            for m in members:
                self.assertEqual(m.db.experience, 10)
                self.assertTrue(m.msg.called)

    def test_engine_stops_when_empty(self):
        a = Dummy()
        a.traits.health = MagicMock(value=a.hp)
        a.key = "dummy"
        a.tags = MagicMock()
        with patch('world.system.state_manager.apply_regen'), \
             patch('combat.engine.damage_processor.delay') as mock_delay, \
             patch('random.randint', return_value=0):
            engine = CombatEngine([a], round_time=0)
            engine.queue_action(a, KillAction(a, a))
            engine.start_round()
            engine.process_round()
            self.assertEqual(len(engine.participants), 0)
            mock_delay.assert_not_called()

    def test_schedules_next_round(self):
        a = Dummy()
        b = Dummy()
        with patch('world.system.state_manager.apply_regen'), \
             patch('world.system.state_manager.get_effective_stat', return_value=0), \
             patch('combat.engine.damage_processor.delay') as mock_delay, \
             patch('random.randint', return_value=0):
            engine = CombatEngine([a, b], round_time=0)
            engine.start_round()
            engine.process_round()
            self.assertEqual(len(engine.participants), 2)
            mock_delay.assert_called_with(0, engine.process_round)

    def test_condition_messages_broadcast(self):
        class DamageAction(Action):
            def resolve(self):
                return CombatResult(self.actor, self.target, "hit", damage=2)

        class MissAction(Action):
            def resolve(self):
                return CombatResult(self.actor, self.target, "miss")

        for act_cls in (DamageAction, MissAction):
            a = Dummy()
            b = Dummy()
            a.key = "attacker"
            b.key = "victim"
            room = MagicMock()
            a.location = b.location = room

            with patch('world.system.state_manager.apply_regen'), \
                 patch('world.system.state_manager.get_effective_stat', return_value=0), \
                 patch('random.randint', return_value=0), \
                 patch('combat.engine.damage_processor.delay'):
                engine = CombatEngine([a, b], round_time=0)
                engine.queue_action(a, act_cls(a, b))
                engine.start_round()
                engine.process_round()

            expected = get_condition_msg(b.hp, b.traits.health.max)
            calls = [c.args[0] for c in room.msg_contents.call_args_list]
            self.assertFalse(any(f"The {b.key} {expected}" in msg for msg in calls))
            room.reset_mock()

    @override_settings(COMBAT_DEBUG_SUMMARY=True)
    def test_damage_summary_broadcast(self):
        class DamageAction(Action):
            def resolve(self):
                return CombatResult(self.actor, self.target, "hit", damage=3)

        a = Dummy()
        b = Dummy()
        a.key = "attacker"
        b.key = "victim"
        room = MagicMock()
        a.location = b.location = room

        with patch('world.system.state_manager.apply_regen'), \
             patch('world.system.state_manager.get_effective_stat', return_value=0), \
             patch('random.randint', return_value=0), \
             patch('combat.engine.damage_processor.delay'):
            engine = CombatEngine([a, b], round_time=0)
            engine.queue_action(a, DamageAction(a, b))
            engine.start_round()
            engine.process_round()

        calls = [c.args[0] for c in room.msg_contents.call_args_list]
        self.assertTrue(any("attacker dealt 3 damage" in msg for msg in calls))

    def test_participant_without_hp_removed(self):
        a = Dummy()
        b = NoHealth()
        a.db.combat_target = b
        b.db.combat_target = a

        with patch('world.system.state_manager.apply_regen'), \
             patch('random.randint', return_value=0):
            engine = CombatEngine([a, b], round_time=0)
            engine.start_round()
            engine.process_round()

        self.assertNotIn(b, [p.actor for p in engine.participants])

    def test_remove_participant_marks_not_in_combat(self):
        a = Dummy()
        b = Dummy()

        engine = CombatEngine([a, b], round_time=0)

        a.on_exit_combat.reset_mock()

        engine.remove_participant(a)

        self.assertFalse(a.db.in_combat)
        self.assertIsNone(getattr(a.db, "combat_target", None))
        a.on_exit_combat.assert_called()
        self.assertNotIn(a, [p.actor for p in engine.participants])


@override_settings(DEFAULT_HOME="#1")
class TestCombatDeath(EvenniaTest):
    def test_npc_death_creates_corpse_and_awards_xp(self):
        from evennia.utils import create
        from typeclasses.characters import NPC

        player = self.char1
        player.db.experience = 0
        npc = create.create_object(NPC, key="mob", location=self.room1)
        npc.db.drops = []
        npc.db.exp_reward = 5
        npc.db.coin_drop = {"silver": 3}
        self.char1.db.coins = from_copper(0)
        item = create.create_object("typeclasses.objects.Object", key="loot", location=npc)
        weapon = create.create_object("typeclasses.objects.Object", key="sword")
        weapon.tags.add("equipment", category="flag")
        weapon.tags.add("identified", category="flag")
        npc.db.equipment = {"mainhand": weapon}
        weapon.location = None

        with patch('world.system.state_manager.apply_regen'), \
             patch('world.system.state_manager.check_level_up'):
            npc.on_death(player)

        self.assertEqual(player.db.experience, 5)
        self.assertEqual(to_copper(player.db.coins), to_copper({"silver": 3}))
        corpse = next(
            obj for obj in self.room1.contents
            if obj.is_typeclass('typeclasses.objects.Corpse', exact=False)
        )
        self.assertEqual(corpse.db.corpse_of, npc.key)
        self.assertEqual(corpse.db.desc, f"The corpse of {npc.key} lies here.")
        self.assertIn(item, corpse.contents)
        self.assertIn(weapon, corpse.contents)

    def test_npc_death_creates_only_one_corpse(self):
        from evennia.utils import create
        from typeclasses.characters import NPC

        player = self.char1
        npc = create.create_object(NPC, key="mob", location=self.room1)
        npc.db.drops = []

        engine = CombatEngine([player, npc], round_time=0)
        engine.queue_action(player, KillAction(player, npc))

        with patch("world.system.state_manager.apply_regen"):
            engine.start_round()
            engine.process_round()

        corpses = [
            obj
            for obj in self.room1.contents
            if obj.is_typeclass("typeclasses.objects.Corpse", exact=False)
        ]
        self.assertEqual(len(corpses), 1)

    def test_same_key_npcs_create_multiple_corpses(self):
        """Killing NPCs with the same key should spawn separate corpses."""
        from evennia.utils import create
        from typeclasses.characters import NPC

        npc1 = create.create_object(NPC, key="mob", location=self.room1)
        npc2 = create.create_object(NPC, key="mob", location=self.room1)
        for npc in (npc1, npc2):
            npc.db.drops = []
            npc.on_death(self.char1)

        corpses = [
            obj
            for obj in self.room1.contents
            if obj.is_typeclass("typeclasses.objects.Corpse", exact=False)
        ]
        self.assertEqual(len(corpses), 2)

    def test_corpse_decay_script(self):
        from evennia.utils import create
        from typeclasses.characters import NPC

        player = self.char1
        npc = create.create_object(NPC, key="mob", location=self.room1)
        npc.db.drops = []
        npc.db.corpse_decay_time = 1

        engine = CombatEngine([player, npc], round_time=0)
        engine.queue_action(player, KillAction(player, npc))

        with patch("world.system.state_manager.apply_regen"):
            engine.start_round()
            engine.process_round()

        corpse = next(
            obj
            for obj in self.room1.contents
            if obj.is_typeclass("typeclasses.objects.Corpse", exact=False)
        )
        script = corpse.scripts.get("decay")[0]
        self.assertEqual(script.interval, 60)
        script.at_repeat()
        self.assertNotIn(corpse, self.room1.contents)

    def test_on_death_handles_deleted_combat_script(self):
        """NPC.on_death should handle a deleted combat script gracefully."""
        from evennia.utils import create
        from typeclasses.characters import NPC

        player = self.char1
        npc = create.create_object(NPC, key="mob", location=self.room1)
        npc.db.drops = []

        from combat.combat_manager import CombatRoundManager
        manager = CombatRoundManager.get()
        instance = manager.start_combat([player, npc])
        manager.remove_combat(instance.combat_id)

        # should not raise when combat script has been removed
        npc.on_death(player)

        corpse = next(
            obj
            for obj in self.room1.contents
            if obj.is_typeclass("typeclasses.objects.Corpse", exact=False)
        )
        self.assertEqual(corpse.db.corpse_of, npc.key)

    def test_out_of_combat_kill_awards_xp(self):
        from evennia.utils import create
        from typeclasses.characters import NPC

        player = self.char1
        player.db.experience = 0
        npc = create.create_object(NPC, key="mob", location=self.room1)
        npc.db.drops = []
        npc.db.exp_reward = 7

        with patch('world.system.state_manager.check_level_up'):
            npc.at_damage(player, npc.traits.health.current + 1)

        self.assertEqual(player.db.experience, 7)

    def test_default_exp_reward_based_on_level(self):
        from evennia.utils import create
        from typeclasses.characters import NPC

        player = self.char1
        player.db.experience = 0
        npc = create.create_object(NPC, key="mob", location=self.room1)
        npc.db.drops = []
        npc.db.level = 3
        npc.db.combat_class = "Warrior"

        npc_builder.finalize_mob_prototype(self.char1, npc)
        expected = (npc.db.level or 1) * settings.DEFAULT_XP_PER_LEVEL
        self.assertEqual(npc.db.exp_reward, expected)

        with patch('world.system.state_manager.check_level_up'):
            npc.at_damage(player, npc.traits.health.current + 1)

        self.assertEqual(player.db.experience, expected)

    def test_npc_on_death_sets_flag_and_moves_out(self):
        from evennia.utils import create
        from typeclasses.characters import NPC

        npc = create.create_object(NPC, key="mob", location=self.room1)
        npc.db.drops = []
        npc.db.vnum = 77

        with patch.object(npc, "delete") as mock_delete:
            npc.on_death(self.char1)
            corpse = next(
                obj
                for obj in self.room1.contents
                if obj.is_typeclass("typeclasses.objects.Corpse", exact=False)
            )
            self.assertEqual(corpse.db.npc_vnum, 77)
            self.assertTrue(npc.db.is_dead)
            self.assertIsNone(npc.location)
            mock_delete.assert_called_once()

    def test_unsaved_npc_death_creates_corpse_and_awards_xp(self):
        from evennia.utils import create
        from typeclasses.characters import NPC

        player = self.char1
        player.db.experience = 0
        npc = create.create_object(NPC, key="mob", location=self.room1)
        npc.db.drops = []
        npc.db.exp_reward = 2
        npc.pk = None

        with patch('world.system.state_manager.apply_regen'), \
             patch('world.system.state_manager.check_level_up'):
            npc.on_death(player)

        self.assertEqual(player.db.experience, 2)
        corpse = next(
            obj
            for obj in self.room1.contents
            if obj.is_typeclass('typeclasses.objects.Corpse', exact=False)
        )
        self.assertEqual(corpse.db.corpse_of, npc.key)

    def test_kill_broadcasts_and_awards_message(self):
        """Killing an NPC should broadcast and award experience."""
        from evennia.utils import create
        from typeclasses.characters import NPC

        player = self.char1
        player.db.experience = 0
        npc = create.create_object(NPC, key="mob", location=self.room1)
        npc.db.drops = []
        npc.db.exp_reward = 5

        self.room1.msg_contents = MagicMock()
        player.msg = MagicMock()

        with patch('world.system.state_manager.apply_regen'), \
             patch('world.system.state_manager.check_level_up'):
            npc.on_death(player)

        calls = [c.args[0] for c in self.room1.msg_contents.call_args_list]
        self.assertTrue(any("is |Rslain|n" in msg for msg in calls))
        self.assertTrue(any("You gain" in c.args[0] for c in player.msg.call_args_list))

    def test_npc_death_uses_engine_xp_award(self):
        """NPC.on_death should delegate XP distribution to the combat engine."""
        from evennia.utils import create
        from typeclasses.characters import NPC

        player = self.char1
        npc = create.create_object(NPC, key="mob", location=self.room1)
        npc.db.drops = []

        engine = CombatEngine([player, npc], round_time=0)
        engine.queue_action(player, KillAction(player, npc))

        with patch('world.system.state_manager.apply_regen'), \
             patch('world.system.state_manager.check_level_up'), \
             patch.object(engine, 'award_experience') as mock_award:
            engine.start_round()
            engine.process_round()

        mock_award.assert_called_once_with(player, npc)

    def test_corpse_stores_vnum_and_npc_removed(self):
        """Corpse retains NPC vnum and NPC removed from room after death."""
        from evennia.utils import create
        from typeclasses.characters import NPC

        player = self.char1
        npc = create.create_object(NPC, key="mob", location=self.room1)
        npc.db.vnum = 42
        npc.db.drops = []

        with patch('world.system.state_manager.apply_regen'), \
             patch('world.system.state_manager.check_level_up'):
            npc.on_death(player)

        corpse = next(
            obj
            for obj in self.room1.contents
            if obj.is_typeclass('typeclasses.objects.Corpse', exact=False)
        )
        self.assertEqual(corpse.db.npc_vnum, npc.db.vnum)
        self.assertNotIn(npc, self.room1.contents)

    def test_health_current_defeat_creates_corpse(self):
        """NPCs with zero current health should die and leave a corpse."""
        from evennia.utils import create
        from typeclasses.characters import NPC

        player = self.char1
        npc = create.create_object(NPC, key="mob", location=self.room1)
        npc.db.drops = []

        class KillCurrent(Action):
            def resolve(self):
                npc.traits.health.current = 0
                return CombatResult(self.actor, npc, "boom")

        engine = CombatEngine([player, npc], round_time=0)
        engine.queue_action(player, KillCurrent(player, npc))

        with patch("world.system.state_manager.apply_regen"), patch("random.randint", return_value=0):
            engine.start_round()
            engine.process_round()

        corpse = next(
            obj
            for obj in self.room1.contents
            if obj.is_typeclass("typeclasses.objects.Corpse", exact=False)
        )
        self.assertNotIn(npc, [p.actor for p in engine.participants])
        self.assertEqual(corpse.db.corpse_of, npc.key)

    def test_player_kills_multiple_npcs_creates_multiple_corpses_and_awards_xp(self):
        """Killing two NPCs should produce two corpses, loot, and combined XP."""
        from evennia.utils import create
        from typeclasses.characters import NPC

        player = self.char1
        player.db.experience = 0
        npc1 = create.create_object(NPC, key="mob1", location=self.room1)
        npc2 = create.create_object(NPC, key="mob2", location=self.room1)

        for npc in (npc1, npc2):
            npc.db.drops = []
        npc1.db.exp_reward = 5
        npc2.db.exp_reward = 7

        loot1 = create.create_object("typeclasses.objects.Object", key="loot1", location=npc1)
        loot2 = create.create_object("typeclasses.objects.Object", key="loot2", location=npc2)

        engine = CombatEngine([player, npc1, npc2], round_time=0)

        # Kill first NPC
        engine.queue_action(player, KillAction(player, npc1))
        with patch("world.system.state_manager.apply_regen"), patch(
            "world.system.state_manager.check_level_up"
        ), patch("random.randint", return_value=0):
            engine.start_round()
            engine.process_round()

        # Kill second NPC
        engine.queue_action(player, KillAction(player, npc2))
        with patch("world.system.state_manager.apply_regen"), patch(
            "world.system.state_manager.check_level_up"
        ), patch("random.randint", return_value=0):
            engine.process_round()

        # Verify two corpses were created
        corpses = [
            obj
            for obj in self.room1.contents
            if obj.is_typeclass("typeclasses.objects.Corpse", exact=False)
        ]
        self.assertEqual(len(corpses), 2)

        # Verify correct corpse mapping
        corpse1 = next(c for c in corpses if c.db.corpse_of == npc1.key)
        corpse2 = next(c for c in corpses if c.db.corpse_of == npc2.key)

        # Verify loot transfer
        self.assertIn(loot1, corpse1.contents)
        self.assertIn(loot2, corpse2.contents)

        # Verify combined XP award
        total_xp = npc1.db.exp_reward + npc2.db.exp_reward
        self.assertEqual(player.db.experience, total_xp)

    def test_manual_death_when_flagged_in_combat_creates_corpse(self):
        """Setting hp to 0 outside the engine should still create a corpse."""
        from evennia.utils import create
        from typeclasses.characters import NPC

        npc = create.create_object(NPC, key="mob", location=self.room1)
        npc.db.drops = []
        npc.db.in_combat = True
        npc.traits.health.current = 0

        corpse = create.create_object('typeclasses.objects.Object', key='corpse', location=None)

        with patch('world.system.state_manager.check_level_up'), \
             patch('typeclasses.scripts.CorpseSpawner.spawn_for', return_value=corpse) as mock_spawn:
            npc.at_damage(self.char1, 0)

        mock_spawn.assert_called_once_with(npc, self.char1)
        self.assertIs(corpse.location, self.room1)

    def test_multi_target_kill_spawns_corpses_and_awards_xp(self):
        """Killing two NPCs at once should create two corpses and grant XP."""
        from evennia.utils import create
        from typeclasses.characters import NPC

        player = self.char1
        player.db.experience = 0
        npc1 = create.create_object(NPC, key="mob1", location=self.room1)
        npc2 = create.create_object(NPC, key="mob2", location=self.room1)

        for npc in (npc1, npc2):
            npc.db.drops = []
            npc.db.exp_reward = 3
            npc.ndb.damage_log = {player: 5}

        class KillBoth(Action):
            def __init__(self, actor, target, other):
                super().__init__(actor, target)
                self.other = other

            def resolve(self):
                npc1.traits.health.current = 0
                npc2.traits.health.current = 0
                return CombatResult(self.actor, npc1, "boom")

        engine = CombatEngine([player, npc1, npc2], round_time=0)
        engine.queue_action(player, KillBoth(player, npc1, npc2))

        with patch("world.system.state_manager.apply_regen"), patch(
            "world.system.state_manager.check_level_up"
        ), patch("random.randint", return_value=0):
            engine.start_round()
            engine.process_round()

        corpses = [
            obj
            for obj in self.room1.contents
            if obj.is_typeclass("typeclasses.objects.Corpse", exact=False)
        ]
        self.assertEqual(len(corpses), 2)
        self.assertIn(npc1.key, [c.db.corpse_of for c in corpses])
        self.assertIn(npc2.key, [c.db.corpse_of for c in corpses])
        self.assertEqual(player.db.experience, npc1.db.exp_reward + npc2.db.exp_reward)


class TestCombatNPCTurn(EvenniaTest):
    def test_at_combat_turn_auto_attack(self):
        from evennia.utils import create
        from typeclasses.npcs import CombatNPC
        from combat.combat_actions import AttackAction

        npc = create.create_object(CombatNPC, key="mob", location=self.room1)
        target = self.char1
        target.location = self.room1
        npc.db.auto_attack_enabled = True
        npc.db.combat_target = target

        engine = CombatEngine([npc, target], round_time=0)

        with patch('world.system.state_manager.apply_regen'), \
             patch('world.system.state_manager.get_effective_stat', return_value=0), \
             patch('random.randint', return_value=0), \
             patch('combat.engine.damage_processor.delay'), \
             patch.object(engine, 'queue_action', wraps=engine.queue_action) as mock_queue:
            engine.start_round()
            engine.process_round()

        self.assertTrue(any(isinstance(c.args[1], AttackAction) for c in mock_queue.call_args_list))


class TestMultipleActions(unittest.TestCase):
    def test_all_queued_actions_execute_in_order(self):
        record = []

        class RecordAction(Action):
            def __init__(self, actor, target, label, priority=0):
                super().__init__(actor, target)
                self.label = label
                self.priority = priority

            def resolve(self):
                record.append(self.label)
                return CombatResult(self.actor, self.target, self.label)

        a = Dummy()
        b = Dummy()
        engine = CombatEngine([a, b], round_time=0)

        engine.queue_action(a, RecordAction(a, b, "first", priority=1))
        engine.queue_action(a, RecordAction(a, b, "second", priority=5))

        with patch("world.system.state_manager.apply_regen"), patch("random.randint", return_value=0):
            engine.start_round()
            engine.process_round()

        self.assertEqual(record, ["second", "first"])

    def test_queue_persists_if_round_interrupted(self):
        class DamageAction(Action):
            def resolve(self):
                return CombatResult(self.actor, self.target, "hit", damage=1)

        a = Dummy()
        b = Dummy()
        engine = CombatEngine([a, b], round_time=0)

        first = DamageAction(a, b)
        second = DamageAction(a, b)

        engine.queue_action(a, first)
        engine.queue_action(a, second)

        with patch("world.system.state_manager.apply_regen"), \
             patch("random.randint", return_value=0), \
             patch.object(engine, "track_aggro", side_effect=Exception("stop")):
            engine.start_round()
            with self.assertRaises(Exception):
                engine.process_round()

        participant = next(p for p in engine.participants if p.actor is a)
        self.assertEqual(participant.next_action, [second])


def test_no_recovery_message_after_target_cleared():
    player = Dummy()
    mob = Dummy()
    player.location = mob.location

    engine = CombatEngine([player, mob], round_time=0)
    engine.queue_action(player, KillAction(player, mob))

    with patch("world.system.state_manager.apply_regen"), \
         patch("combat.engine.damage_processor.delay"), \
         patch("random.randint", return_value=0):
        engine.start_round()
        engine.process_round()

        player.msg.reset_mock()
        player.db.combat_target = None
        player.cooldowns.ready.return_value = False

        engine.process_round()

    messages = [call.args[0] for call in player.msg.call_args_list]
    assert "Still recovering." not in messages


class TestUnsavedPrototypeCombat(unittest.TestCase):
    def test_combat_with_unsaved_npc(self):
        player = Dummy()
        npc = UnsavedDummy()
        engine = CombatEngine([player, npc], round_time=0)
        engine.queue_action(player, KillAction(player, npc))

        with patch("world.system.state_manager.apply_regen"), \
             patch("world.system.state_manager.check_level_up"), \
             patch("world.system.state_manager.get_effective_stat", return_value=0), \
             patch("random.randint", return_value=0), \
             patch("combat.engine.damage_processor.delay"):
            engine.start_round()
            engine.process_round()

        self.assertNotIn(npc, [p.actor for p in engine.participants])

    def test_track_aggro_ignores_unsaved(self):
        player = Dummy()
        npc = UnsavedDummy()
        engine = CombatEngine([player], round_time=0)

        with patch("world.system.state_manager.get_effective_stat", return_value=0):
            engine.track_aggro(npc, player)
            engine.track_aggro(player, npc)

        self.assertFalse(engine.aggro)


class TestCleanupEnvironment(EvenniaTest):
    def test_cleanup_removes_dead_actor(self):
        from evennia.utils import create
        from typeclasses.characters import NPC
        from combat.engine import CombatEngine
        from combat.combat_manager import CombatRoundManager

        npc = create.create_object(NPC, key="dead", location=self.room1)
        player = self.char1

        engine = CombatEngine([player, npc], round_time=0)
        npc.db.is_dead = True

        manager = CombatRoundManager.get()
        manager.combats.clear()
        manager.combatant_to_combat.clear()

        engine.processor.cleanup_environment()

        self.assertNotIn(npc, [p.actor for p in engine.participants])


def test_attacker_target_cleared_on_defeat():
    attacker = Dummy()
    defender = Dummy()
    attacker.db.combat_target = defender
    defender.db.combat_target = attacker

    engine = CombatEngine([attacker, defender], round_time=0)
    engine.queue_action(attacker, KillAction(attacker, defender))

    with patch("world.system.state_manager.apply_regen"), \
         patch("random.randint", return_value=0):
        engine.start_round()
        engine.process_round()

    assert attacker.db.combat_target is None


def test_clearing_target_leaves_combat():
    player = Dummy()
    mob = Dummy()
    player.location = mob.location
    player.db.combat_target = mob
    mob.db.combat_target = player

    engine = CombatEngine([player, mob], round_time=0)

    with patch("world.system.state_manager.apply_regen"), \
         patch("combat.engine.damage_processor.delay"), \
         patch("random.randint", return_value=0):
        engine.start_round()
        engine.process_round()

        player.db.combat_target = None
        engine.process_round()

    assert player in [p.actor for p in engine.participants]


def test_retarget_after_defeat():
    a = Dummy()
    b1 = Dummy()
    b2 = Dummy()
    a.location = b1.location = b2.location
    a.db.combat_target = b1
    b1.db.combat_target = a
    b2.db.combat_target = a

    engine = CombatEngine([a, b1, b2], round_time=0)
    engine.queue_action(a, KillAction(a, b1))

    with patch("world.system.state_manager.apply_regen"), patch("random.randint", return_value=0):
        engine.start_round()
        engine.process_round()

    assert a.db.combat_target is b2


def test_remaining_combatants_continue_after_kill():
    player = Dummy()
    mob1 = Dummy()
    mob2 = Dummy()
    player.key = "player"
    mob1.key = "mob1"
    mob2.key = "mob2"
    player.location = mob1.location = mob2.location
    player.db.combat_target = mob1
    mob1.db.combat_target = player
    mob2.db.combat_target = player
    for obj in (player, mob1, mob2):
        obj.db.active_effects = {}

    engine = CombatEngine([player, mob1, mob2], round_time=0)
    engine.queue_action(player, KillAction(player, mob1))

    with patch("world.system.state_manager.apply_regen"), patch(
        "random.randint", return_value=0
    ):
        engine.start_round()
        engine.process_round()
        engine.process_round()

    assert mob2 in [p.actor for p in engine.participants]
    assert player.db.combat_target is mob2


def test_dead_actor_action_skipped():
    player = Dummy()
    mob1 = Dummy()
    mob2 = Dummy()
    player.location = mob1.location = mob2.location
    player.db.combat_target = mob1
    mob1.db.combat_target = player
    mob2.db.combat_target = player

    engine = CombatEngine([player, mob1, mob2], round_time=0)
    engine.queue_action(player, KillAction(player, mob1))
    engine.queue_action(mob1, AttackAction(mob1, player))

    with patch("world.system.state_manager.apply_regen"), patch(
        "random.randint", return_value=0
    ):
        engine.start_round()
        engine.process_round()
        engine.process_round()

    assert mob2 in [p.actor for p in engine.participants]
    assert player.db.combat_target is mob2


def test_queue_pruned_after_defeat():
    player = Dummy()
    mob1 = Dummy()
    mob2 = Dummy()
    player.key = "player"
    mob1.key = "mob1"
    mob2.key = "mob2"
    player.location = mob1.location = mob2.location
    player.db.combat_target = mob1
    mob1.db.combat_target = player
    mob2.db.combat_target = player

    engine = CombatEngine([player, mob1, mob2], round_time=0)
    engine.queue_action(player, KillAction(player, mob1))
    class MarkAction(Action):
        def resolve(self):
            return CombatResult(self.actor, self.target, "mark")

    engine.queue_action(player, MarkAction(player, mob1))

    def _dummy_attack(self):
        return CombatResult(self.actor, self.target, "atk")

    with patch("world.system.state_manager.apply_regen"), patch(
        "world.system.state_manager.get_effective_stat", return_value=0
    ), patch(
        "combat.combat_actions.AttackAction.resolve", _dummy_attack
    ), patch(
        "random.randint", return_value=0
    ):
        engine.start_round()
        engine.process_round()
        participant = next(p for p in engine.participants if p.actor is player)
        assert not any(getattr(a, "target", None) is mob1 for a in participant.next_action)
        engine.queue_action(player, MarkAction(player, mob2))
        engine.process_round()

    assert mob2 in [p.actor for p in engine.participants]
    assert player.db.combat_target is mob2


def test_hostile_joins_after_midround_kill():
    player = Dummy()
    mob1 = Dummy()
    mob2 = Dummy()
    room = MagicMock()
    player.location = mob1.location = mob2.location = room

    player.db.combat_target = mob1
    mob1.db.combat_target = player
    mob2.db.combat_target = player

    from combat.combat_manager import CombatRoundManager

    manager = CombatRoundManager.get()
    manager.combats.clear()
    manager.combatant_to_combat.clear()
    inst = manager.start_combat([player, mob1])

    engine = inst.engine
    engine.queue_action(player, KillAction(player, mob1))

    with patch("world.system.state_manager.apply_regen"), patch(
        "random.randint", return_value=0
    ):
        inst.process_round()
        inst.process_round()

    assert mob2 in [p.actor for p in engine.participants]
    assert player.db.combat_target is mob2


def test_multi_combat_until_one_remains():
    player = Dummy()
    mobs = [Dummy() for _ in range(4)]
    player.key = "player"
    for i, mob in enumerate(mobs, start=1):
        mob.key = f"mob{i}"
    room = MagicMock()
    for obj in [player] + mobs:
        obj.location = room
        obj.db.active_effects = {}

    player.db.combat_target = mobs[0]
    mobs[0].db.combat_target = player
    mobs[1].db.combat_target = mobs[0]
    mobs[2].db.combat_target = mobs[1]
    mobs[3].db.combat_target = mobs[2]

    engine = CombatEngine([player] + mobs, round_time=0)

    with patch("world.system.state_manager.apply_regen"), patch(
        "random.randint", return_value=0
    ):
        engine.start_round()

        # kill mobs one at a time
        engine.queue_action(player, KillAction(player, mobs[0]))
        engine.process_round()
        assert mobs[0] not in [p.actor for p in engine.participants]
        assert player.db.combat_target is mobs[1]
        assert mobs[1].db.combat_target is player
        assert mobs[2].db.combat_target is mobs[1]
        assert mobs[3].db.combat_target is mobs[2]

        engine.queue_action(player, KillAction(player, mobs[1]))
        engine.process_round()
        assert mobs[1] not in [p.actor for p in engine.participants]
        assert player.db.combat_target is mobs[2]
        assert mobs[2].db.combat_target is player
        assert mobs[3].db.combat_target is mobs[2]

        engine.queue_action(player, KillAction(player, mobs[2]))
        engine.process_round()
        assert player.db.combat_target is mobs[3]
        assert mobs[3].db.combat_target is player

        engine.queue_action(player, KillAction(player, mobs[3]))
        engine.process_round()

    assert not engine.participants
    assert player.db.combat_target is None


def test_health_current_defeat_removes_participant():
    class Trait:
        def __init__(self, val):
            self.value = val
            self.current = val
            self.max = val

    class CurrentDummy(Dummy):
        def __init__(self, hp=10, init=0):
            super().__init__(hp, init)
            self.traits.health = Trait(hp)

    class KillCurrent(Action):
        def resolve(self):
            self.target.traits.health.current = 0
            return CombatResult(self.actor, self.target, "boom")

    attacker = Dummy()
    defender = CurrentDummy()
    attacker.db.combat_target = defender
    defender.db.combat_target = attacker

    engine = CombatEngine([attacker, defender], round_time=0)
    engine.queue_action(attacker, KillCurrent(attacker, defender))

    with patch("world.system.state_manager.apply_regen"), patch("random.randint", return_value=0):
        engine.start_round()
        engine.process_round()

    assert defender.traits.health.value > 0
    assert defender not in [p.actor for p in engine.participants]

