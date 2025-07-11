"""
Tests for custom character logic
"""

from unittest.mock import MagicMock, call, patch
from evennia.utils.test_resources import EvenniaTest
from django.test import override_settings
from evennia.utils import create
from evennia.scripts.models import ScriptDB
from server.conf import at_server_startstop


@override_settings(DEFAULT_HOME=None)
class TestCharacterHooks(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.char1.msg = MagicMock()
        self.char2.msg = MagicMock()

    def test_at_pre_move(self):
        self.char1.tags.add("lying down", category="status")
        self.char1.execute_cmd("out")
        self.char1.msg.assert_any_call("You can't move while you're lying down.")
        self.char1.msg.reset_call()
        self.char1.tags.add("unconscious", category="status")
        self.char1.execute_cmd("out")
        self.char1.msg.assert_any_call(
            "You can't move while you're lying down or unconscious."
        )

    def test_at_damage(self):
        self.char2.at_damage(self.char1, 10)
        self.char2.msg.assert_called_once_with("You take 10 damage from |gChar|n.")
        self.char2.msg.reset_call()
        self.char2.at_damage(self.char1, 90)
        self.char2.msg.assert_any_call("You take 90 damage from |gChar|n.")
        calls = [c.args[0] for c in self.char2.msg.call_args_list if c.args]
        self.assertTrue(any("You fall unconscious" in c for c in calls))

    def test_at_damage_handles_none_log(self):
        """Ensure damage_log defaults to an empty dict when set to None."""
        self.char2.ndb.damage_log = None
        self.char2.at_damage(self.char1, 5)
        self.assertEqual(self.char2.ndb.damage_log.get(self.char1), 5)

    def test_at_damage_no_attacker(self):
        """Calling at_damage with no attacker should not error."""
        self.char2.at_damage(None, 10)
        self.char2.msg.assert_called_once_with("You take 10 damage.")
        self.char1.msg.assert_not_called()

    def test_at_wield_unwield(self):
        self.char1.attributes.add("_wielded", {"left": None, "right": None})
        used_hands = self.char1.at_wield(self.obj1)
        self.assertEqual(len(used_hands), 1)
        self.assertIn(self.obj1, self.char1.wielding)
        freed_hands = self.char1.at_unwield(self.obj1)
        self.assertEqual(used_hands, freed_hands)

    def test_at_wield_offhand(self):
        self.char1.attributes.add("_wielded", {"left": None, "right": None})
        self.char1.db.handedness = "right"
        weapon = create.create_object(
            "typeclasses.gear.MeleeWeapon", key="weap", location=self.char1
        )
        weapon.tags.add("equipment", category="flag")
        weapon.tags.add("identified", category="flag")
        weapon.tags.add("offhand", category="flag")
        used = self.char1.at_wield(weapon)
        self.assertEqual(used, ["left"])

    def test_at_wield_replaces_existing(self):
        self.char1.attributes.add("_wielded", {"left": None, "right": None})
        weapon1 = create.create_object(
            "typeclasses.gear.MeleeWeapon", key="sword", location=self.char1
        )
        weapon1.tags.add("equipment", category="flag")
        weapon1.tags.add("identified", category="flag")

        weapon2 = create.create_object(
            "typeclasses.gear.MeleeWeapon", key="axe", location=self.char1
        )
        weapon2.tags.add("equipment", category="flag")
        weapon2.tags.add("identified", category="flag")

        self.char1.at_wield(weapon1, hand="right")
        self.assertIn(weapon1, self.char1.wielding)

        self.char1.at_wield(weapon2, hand="right")
        self.assertIn(weapon2, self.char1.wielding)
        self.assertNotIn(weapon1, self.char1.wielding)

    def test_twohanded_blocked_by_shield(self):
        self.char1.attributes.add("_wielded", {"left": None, "right": None})
        shield = create.create_object(
            "typeclasses.objects.ClothingObject", key="shield", location=self.char1
        )
        shield.tags.add("equipment", category="flag")
        shield.tags.add("identified", category="flag")
        shield.tags.add("shield", category="flag")
        shield.wear(self.char1, True)
        # attempt to wield two-handed weapon
        weapon = create.create_object(
            "typeclasses.gear.MeleeWeapon", key="great", location=self.char1
        )
        weapon.tags.add("equipment", category="flag")
        weapon.tags.add("identified", category="flag")
        weapon.tags.add("twohanded", category="flag")
        self.assertIsNone(self.char1.at_wield(weapon))
        self.assertNotIn(weapon, self.char1.wielding)

    def test_wear_shield_blocked_by_twohanded(self):
        self.char1.attributes.add("_wielded", {"left hand": None, "right hand": None})
        weapon = create.create_object(
            "typeclasses.gear.MeleeWeapon", key="great", location=self.char1
        )
        weapon.tags.add("equipment", category="flag")
        weapon.tags.add("identified", category="flag")
        weapon.tags.add("twohanded", category="flag")
        self.char1.at_wield(weapon)
        shield = create.create_object(
            "typeclasses.objects.ClothingObject", key="shield", location=self.char1
        )
        shield.tags.add("equipment", category="flag")
        shield.tags.add("identified", category="flag")
        shield.tags.add("shield", category="flag")
        shield.wear(self.char1, True)
        self.assertFalse(shield.db.worn)

    def test_arrive_depart_hooks(self):
        npc = create.create_object("typeclasses.characters.NPC", key="mob", location=self.room1)

        self.char1.refresh_prompt = MagicMock()
        npc.check_triggers = MagicMock()

        # character enters the room
        self.char2.location = self.room2
        self.char2.move_to(self.room1)

        self.char1.refresh_prompt.assert_called()
        npc.check_triggers.assert_called_with("on_enter", chara=self.char2)

        self.char1.refresh_prompt.reset_mock()
        npc.check_triggers.reset_mock()

        # character leaves the room
        self.char2.move_to(self.room2)

        self.char1.refresh_prompt.assert_called()
        npc.check_triggers.assert_called_with("on_leave", chara=self.char2, destination=self.room2)


class TestCharacterDisplays(EvenniaTest):
    def test_get_display_status(self):
        self.assertEqual(
            "|gChar|n - Health 100% : Mana 100% : Stamina 100%",
            self.char1.get_display_status(self.char2),
        )
        self.assertEqual(
            "Health 100% : Mana 100% : Stamina 100%",
            self.char1.get_display_status(self.char1),
        )


class TestCharacterProperties(EvenniaTest):
    def test_wielded_free_hands(self):
        self.char1.attributes.add(
            "_wielded", {"left hand": None, "right hand": self.obj1}
        )
        self.assertEqual(self.char1.wielding, [self.obj1])
        self.assertEqual(self.char1.free_hands, ["left hand"])

    def test_in_combat(self):
        self.assertFalse(self.char1.in_combat)
        from combat.round_manager import CombatRoundManager

        manager = CombatRoundManager.get()
        instance = manager.start_combat([self.char1, self.char2])
        self.assertFalse(self.char1.in_combat)
        instance.add_combatant(self.char1)
        self.assertTrue(self.char1.in_combat)


@override_settings(DEFAULT_HOME=None)
class TestGlobalTick(EvenniaTest):
    def test_interval(self):
        from typeclasses.scripts import GlobalTick

        script = GlobalTick()
        script.at_script_creation()
        self.assertEqual(script.interval, 60)
        self.assertTrue(script.persistent)

    def test_tick_triggers_prompt(self):
        from typeclasses.scripts import GlobalTick

        script = GlobalTick()
        script.at_script_creation()

        self.char1.tags.add("tickable")
        self.char1.at_tick = MagicMock()
        self.char1.refresh_prompt = MagicMock()
        from world.system import state_manager

        original_tick_all = state_manager.tick_all
        state_manager.tick_all = MagicMock(side_effect=original_tick_all)

        script.at_repeat()

        self.char1.at_tick.assert_not_called()
        self.char1.refresh_prompt.assert_called()
        state_manager.tick_all.assert_called_once()

    def test_tick_offline_characters(self):
        from typeclasses.scripts import GlobalTick

        script = GlobalTick()
        script.at_script_creation()

        pc = create.create_object(
            "typeclasses.characters.PlayerCharacter",
            key="Offline PC",
            location=self.room1,
            home=self.room1,
        )
        npc = create.create_object(
            "typeclasses.characters.NPC",
            key="An NPC",
            location=self.room1,
            home=self.room1,
        )

        for char in (pc, npc):
            char.tags.add("tickable")
            for key in ("health", "mana", "stamina"):
                trait = char.traits.get(key)
                trait.current = trait.max // 2

        from world.system import state_manager

        original_tick_all = state_manager.tick_all
        state_manager.tick_all = MagicMock(side_effect=original_tick_all)

        pc.at_tick = MagicMock(side_effect=pc.at_tick)
        npc.at_tick = MagicMock(side_effect=npc.at_tick)

        script.at_repeat()

        pc.at_tick.assert_not_called()
        npc.at_tick.assert_not_called()

        state_manager.tick_all.assert_called_once()

        for char in (pc, npc):
            for key in ("health", "mana", "stamina"):
                trait = char.traits.get(key)
                self.assertGreater(trait.current, trait.max // 2)

    def test_effects_expire_on_tick(self):
        from typeclasses.scripts import GlobalTick

        script = GlobalTick()
        script.at_script_creation()

        self.char1.tags.add("tickable")
        from world.system import state_manager

        original_tick_all = state_manager.tick_all
        state_manager.tick_all = MagicMock(side_effect=original_tick_all)

        state_manager.add_status_effect(self.char1, "stunned", 1)

        script.at_repeat()

        state_manager.tick_all.assert_called_once()
        self.assertFalse(self.char1.tags.has("stunned", category="status"))

    def test_at_server_start_keeps_global_tick_active(self):
        ScriptDB.objects.filter(db_key="global_tick").delete()

        from evennia.scripts import manager as scripts_manager
        original_filter = scripts_manager.ScriptDBManager.filter

        def filter_proxy(self, *args, **kwargs):
            if "typeclass_path" in kwargs:
                kwargs["db_typeclass_path"] = kwargs.pop("typeclass_path")
            return original_filter(self, *args, **kwargs)

        with (
            patch(
                "evennia.scripts.manager.ScriptDBManager.filter",
                new=filter_proxy,
            ),
            patch("utils.mob_proto.load_npc_prototypes"),
            patch("server.conf.at_server_startstop._migrate_experience"),
            patch("server.conf.at_server_startstop._build_caches"),
            patch("server.conf.at_server_startstop._ensure_room_areas"),
            patch("server.conf.at_server_startstop.resume_paused_scripts"),
            patch("world.scripts.mob_db.get_mobdb"),
            patch("server.conf.at_server_startstop.get_respawn_manager"),
            patch("world.scripts.create_midgard_area.create"),
        ):
            at_server_startstop.at_server_start()

        script = ScriptDB.objects.filter(db_key="global_tick").first()
        self.assertIsNotNone(script)
        self.assertTrue(script.is_active)


class TestRegeneration(EvenniaTest):
    def test_at_tick_heals_resources(self):
        from typeclasses.scripts import GlobalTick

        char = self.char1
        char.tags.add("tickable")
        for key in ("health", "mana", "stamina"):
            trait = char.traits.get(key)
            trait.current = trait.max // 2
        char.db.derived_stats = {
            "health_regen": 2,
            "mana_regen": 3,
            "stamina_regen": 4,
        }
        char.refresh_prompt = MagicMock()
        char.msg = MagicMock()

        script = GlobalTick()
        script.at_script_creation()

        script.at_repeat()

        for key, regen in (
            ("health", 2),
            ("mana", 3),
            ("stamina", 4),
        ):
            trait = char.traits.get(key)
            self.assertEqual(trait.current, trait.max // 2 + regen)

        char.refresh_prompt.assert_called_once()
        char.msg.assert_not_called()


class TestCharacterCreationStats(EvenniaTest):
    def test_armor_trait_defaults_to_zero(self):
        char = create.create_object(
            "typeclasses.characters.PlayerCharacter",
            key="Newbie",
            location=self.room1,
            home=self.room1,
        )
        self.assertIsNotNone(char.traits.get("armor"))
        self.assertEqual(char.traits.armor.base, 0)


class TestReviveRespawn(EvenniaTest):
    def test_revive_sets_partial_health_without_regen(self):
        char = self.char1
        char2 = self.char2
        char.traits.health.current = 0
        char.tags.add("unconscious", category="status")
        char.tags.add("lying down", category="status")
        char.traits.health.rate = 1.0
        char.revive(char2)
        self.assertEqual(char.traits.health.current, char.traits.health.max // 5)
        self.assertEqual(char.traits.health.rate, 0.0)
        self.assertFalse(char.tags.has("unconscious", category="status"))


@override_settings(DEFAULT_HOME=None)
class TestCombatResists(EvenniaTest):
    def setUp(self):
        super().setUp()
        from world import stats
        from world.system import stat_manager

        stats.apply_stats(self.char1)
        stats.apply_stats(self.char2)
        stat_manager.refresh_stats(self.char1)
        stat_manager.refresh_stats(self.char2)

        self.weapon = create.create_object(
            "typeclasses.gear.MeleeWeapon", key="sword", location=self.char1
        )
        self.weapon.tags.add("equipment", category="flag")
        self.weapon.tags.add("identified", category="flag")
        self.weapon.db.dmg = 10
        self.weapon.db.status_effect = ("stunned", 50)

    def test_status_resist_prevents_effect(self):
        from world.system import stat_manager
        self.char1.db.stat_overrides = {"hit_chance": 100}
        self.char2.db.stat_overrides = {"status_resist": 60}
        stat_manager.refresh_stats(self.char1)
        stat_manager.refresh_stats(self.char2)
        with patch("world.system.stat_manager.randint", return_value=1):
            self.weapon.at_attack(self.char1, self.char2)
        self.assertFalse(self.char2.tags.has("stunned", category="status"))

        self.char2.db.stat_overrides = {"status_resist": 0}
        stat_manager.refresh_stats(self.char2)
        with patch("world.system.stat_manager.randint", return_value=1):
            self.weapon.at_attack(self.char1, self.char2)
        self.assertTrue(self.char2.tags.has("stunned", category="status"))

    def test_crit_resist_reduces_crit_damage(self):
        from world.system import stat_manager
        self.char1.db.stat_overrides = {
            "hit_chance": 100,
            "crit_chance": 50,
            "crit_bonus": 100,
        }
        base_hp = self.char2.traits.health.current
        stat_manager.refresh_stats(self.char1)

        # No crit resist
        self.char2.db.stat_overrides = {"crit_resist": 0}
        stat_manager.refresh_stats(self.char2)
        with patch("world.system.stat_manager.randint", return_value=1):
            self.weapon.at_attack(self.char1, self.char2)
        self.assertEqual(self.char2.traits.health.current, base_hp - 20)

        # With high crit resist
        self.char2.traits.health.current = base_hp
        self.char2.db.stat_overrides = {"crit_resist": 60}
        stat_manager.refresh_stats(self.char2)
        with patch("world.system.stat_manager.randint", return_value=1):
            self.weapon.at_attack(self.char1, self.char2)
        self.assertEqual(self.char2.traits.health.current, base_hp - 10)

    def test_respawn_restores_full_health_without_regen(self):
        char = self.char1
        char.traits.health.current = 0
        char.tags.add("unconscious", category="status")
        char.tags.add("lying down", category="status")
        char.traits.health.rate = 1.0
        char.respawn()
        self.assertEqual(char.traits.health.current, char.traits.health.max)
        self.assertEqual(char.traits.health.rate, 0.0)
        self.assertFalse(char.tags.has("unconscious", category="status"))

    def test_armor_reduces_damage(self):
        self.char2.traits.armor.base = 10
        base = self.char2.traits.health.current
        self.char2.at_damage(self.char1, 10)
        self.assertEqual(self.char2.traits.health.current, base - 9)

    def test_evasion_prevents_weapon_damage(self):
        self.char2.traits.evasion.base = 100
        with patch("world.system.stat_manager.check_hit", return_value=True), patch(
            "combat.combat_utils.random.randint", return_value=1
        ):
            before = self.char2.traits.health.current
            self.weapon.at_attack(self.char1, self.char2)
            self.assertEqual(self.char2.traits.health.current, before)


class TestPlayerDeath(EvenniaTest):
    def test_player_death_spawns_corpse_with_bodyparts_and_drops_inventory(self):
        from evennia.utils import create
        from typeclasses.objects import Object
        from world.mob_constants import BODYPARTS

        player = self.char1
        attacker = self.char2
        player.db.coins = {"gold": 2}
        item = create.create_object(Object, key="dagger", location=player, nohome=True)

        player.traits.health.current = 1
        player.at_damage(attacker, 2)

        corpses = [
            obj
            for obj in self.room1.contents
            if obj.is_typeclass("typeclasses.objects.Corpse", exact=False)
        ]
        self.assertEqual(len(corpses), 1)
        corpse = corpses[0]
        self.assertEqual(corpse.db.corpse_of, player.key)
        self.assertEqual(corpse.db.corpse_of_id, player.dbref)
        part_names = sorted(
            obj.key for obj in corpse.contents if obj.key in [p.value for p in BODYPARTS]
        )
        expected = sorted(part.value for part in BODYPARTS)
        self.assertEqual(part_names, expected)
        self.assertEqual(item.location, corpse)
        self.assertEqual(player.db.coins.get("gold"), 2)

    def test_player_death_broadcasts_room_message(self):
        player = self.char1
        attacker = self.char2
        self.room1.msg_contents = MagicMock()

        player.traits.health.current = 1
        player.at_damage(attacker, 2)

        calls = [c.args[0] for c in self.room1.msg_contents.call_args_list]
        self.assertTrue(
            any("is slain" in msg or "dies." in msg for msg in calls)
        )

    def test_player_receives_death_message(self):
        player = self.char1
        attacker = self.char2
        player.msg = MagicMock()

        player.traits.health.current = 1
        player.at_damage(attacker, 2)

        player.msg.assert_any_call(
            f"You are slain by {attacker.get_display_name(player)}!"
        )
