from unittest.mock import MagicMock, patch
import unittest
from evennia.utils.test_resources import EvenniaTest

from combat.combat_engine import CombatEngine
from combat.combat_actions import Action, CombatResult
from utils.currency import from_copper, to_copper
from combat.combat_utils import get_condition_msg


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
        self.db = type("DB", (), {"temp_bonuses": {}})()
        self.on_enter_combat = MagicMock()
        self.on_exit_combat = MagicMock()
        self.msg = MagicMock()

    def at_damage(self, attacker, amount, damage_type=None):
        self.hp = max(self.hp - amount, 0)
        if hasattr(self.traits, "health"):
            self.traits.health.value = self.hp
        return amount


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
        attacker.db = type("DB", (), {"exp": 0})()
        victim = Dummy()
        victim.db = type("DB", (), {"exp_reward": 10})()
        with patch('world.system.state_manager.apply_regen'), \
             patch('world.system.state_manager.check_level_up'), \
             patch.object(attacker, 'msg') as mock_msg:
            engine = CombatEngine([attacker, victim], round_time=0)
            engine.queue_action(attacker, KillAction(attacker, victim))
            engine.start_round()
            engine.process_round()
            self.assertEqual(attacker.db.exp, 10)
            mock_msg.assert_called()

    def test_group_gain_splits_exp(self):
        a = Dummy()
        b = Dummy()
        for obj in (a, b):
            obj.db = type("DB", (), {"exp": 0})()
        victim = Dummy()
        victim.db = type("DB", (), {"exp_reward": 9})()
        with patch('world.system.state_manager.apply_regen'), \
             patch('world.system.state_manager.check_level_up'), \
             patch.object(a, 'msg') as msg_a, patch.object(b, 'msg') as msg_b:
            engine = CombatEngine([a, b, victim], round_time=0)
            engine.aggro[victim] = {a: 1, b: 1}
            engine.queue_action(a, KillAction(a, victim))
            engine.start_round()
            engine.process_round()
            self.assertEqual(a.db.exp, 4)
            self.assertEqual(b.db.exp, 4)
            msg_a.assert_called()
            msg_b.assert_called()

    def test_engine_stops_when_empty(self):
        a = Dummy()
        a.traits.health = MagicMock(value=a.hp)
        a.key = "dummy"
        a.tags = MagicMock()
        with patch('world.system.state_manager.apply_regen'), \
             patch('combat.combat_engine.delay') as mock_delay, \
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
             patch('combat.combat_actions.utils.inherits_from', return_value=False), \
             patch('combat.combat_engine.delay') as mock_delay, \
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
                 patch('combat.combat_engine.delay'):
                engine = CombatEngine([a, b], round_time=0)
                engine.queue_action(a, act_cls(a, b))
                engine.start_round()
                engine.process_round()

            expected = get_condition_msg(b.hp, b.traits.health.max)
            calls = [c.args[0] for c in room.msg_contents.call_args_list]
            self.assertTrue(any(f"The {b.key} {expected}" in msg for msg in calls))
            room.reset_mock()

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
             patch('combat.combat_engine.delay'):
            engine = CombatEngine([a, b], round_time=0)
            engine.queue_action(a, DamageAction(a, b))
            engine.start_round()
            engine.process_round()

        calls = [c.args[0] for c in room.msg_contents.call_args_list]
        self.assertTrue(any("attacker dealt 3 damage" in msg for msg in calls))


class TestCombatDeath(EvenniaTest):
    def test_npc_death_creates_corpse_and_awards_xp(self):
        from evennia.utils import create
        from typeclasses.characters import NPC

        player = self.char1
        player.db.exp = 0
        npc = create.create_object(NPC, key="mob", location=self.room1)
        npc.db.drops = []
        npc.db.exp_reward = 5
        npc.db.coin_drop = {"silver": 3}
        self.char1.db.coins = from_copper(0)

        engine = CombatEngine([player, npc], round_time=0)
        engine.queue_action(player, KillAction(player, npc))

        with patch('world.system.state_manager.apply_regen'), \
             patch('world.system.state_manager.check_level_up'):
            engine.start_round()
            engine.process_round()

        self.assertEqual(player.db.exp, 5)
        self.assertEqual(to_copper(player.db.coins), to_copper({"silver": 3}))
        corpse = next(
            obj for obj in self.room1.contents
            if obj.is_typeclass('typeclasses.objects.Corpse', exact=False)
        )
        self.assertEqual(corpse.db.corpse_of, npc.key)
        self.assertEqual(corpse.db.desc, f"The corpse of {npc.key} lies here.")

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
        script = corpse.scripts.get("auto_decay")[0]
        self.assertEqual(script.interval, 60)
        script.at_repeat()
        self.assertNotIn(corpse, self.room1.contents)


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
             patch('combat.combat_actions.utils.inherits_from', return_value=True), \
             patch('random.randint', return_value=0), \
             patch('combat.combat_engine.delay'), \
             patch.object(engine, 'queue_action', wraps=engine.queue_action) as mock_queue:
            engine.start_round()
            engine.process_round()

        self.assertTrue(any(isinstance(c.args[1], AttackAction) for c in mock_queue.call_args_list))
