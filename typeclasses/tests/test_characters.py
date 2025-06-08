"""
Tests for custom character logic
"""

from unittest.mock import MagicMock, call, patch
from evennia.utils.test_resources import EvenniaTest
from django.test import override_settings
from evennia.utils import create


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
        from typeclasses.scripts import CombatScript

        self.room1.scripts.add(CombatScript, key="combat")
        combat_script = self.room1.scripts.get("combat")[0]
        self.assertFalse(self.char1.in_combat)
        combat_script.add_combatant(self.char1, enemy=self.char2)
        self.assertTrue(self.char1.in_combat)


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

        state_manager.tick_character = MagicMock()

        script.at_repeat()

        self.char1.at_tick.assert_not_called()
        self.char1.refresh_prompt.assert_called()
        state_manager.tick_character.assert_not_called()

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

        state_manager.tick_character = MagicMock()

        pc.at_tick = MagicMock(side_effect=pc.at_tick)
        npc.at_tick = MagicMock(side_effect=npc.at_tick)

        script.at_repeat()

        pc.at_tick.assert_not_called()
        npc.at_tick.assert_not_called()

        state_manager.tick_character.assert_not_called()

        for char in (pc, npc):
            for key in ("health", "mana", "stamina"):
                trait = char.traits.get(key)
                self.assertGreater(trait.current, trait.max // 2)


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
        self.char1.db.stat_overrides = {"accuracy": 100}
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
            "accuracy": 100,
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
