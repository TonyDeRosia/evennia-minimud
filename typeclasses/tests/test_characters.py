"""
Tests for custom character logic
"""

from unittest.mock import MagicMock, call, patch
from evennia.utils.test_resources import EvenniaTest
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
        weapon = create.create_object("typeclasses.gear.MeleeWeapon", key="weap", location=self.char1)
        weapon.tags.add("equipment", category="flag")
        weapon.tags.add("identified", category="flag")
        weapon.tags.add("offhand", category="flag")
        used = self.char1.at_wield(weapon)
        self.assertEqual(used, ["left"])

    def test_twohanded_blocked_by_shield(self):
        self.char1.attributes.add("_wielded", {"left": None, "right": None})
        shield = create.create_object("typeclasses.objects.ClothingObject", key="shield", location=self.char1)
        shield.tags.add("equipment", category="flag")
        shield.tags.add("identified", category="flag")
        shield.tags.add("shield", category="flag")
        shield.wear(self.char1, True)
        # attempt to wield two-handed weapon
        weapon = create.create_object("typeclasses.gear.MeleeWeapon", key="great", location=self.char1)
        weapon.tags.add("equipment", category="flag")
        weapon.tags.add("identified", category="flag")
        weapon.tags.add("twohanded", category="flag")
        self.assertIsNone(self.char1.at_wield(weapon))
        self.assertNotIn(weapon, self.char1.wielding)

    def test_wear_shield_blocked_by_twohanded(self):
        self.char1.attributes.add("_wielded", {"left hand": None, "right hand": None})
        weapon = create.create_object("typeclasses.gear.MeleeWeapon", key="great", location=self.char1)
        weapon.tags.add("equipment", category="flag")
        weapon.tags.add("identified", category="flag")
        weapon.tags.add("twohanded", category="flag")
        self.char1.at_wield(weapon)
        shield = create.create_object("typeclasses.objects.ClothingObject", key="shield", location=self.char1)
        shield.tags.add("equipment", category="flag")
        shield.tags.add("identified", category="flag")
        shield.tags.add("shield", category="flag")
        shield.wear(self.char1, True)
        self.assertFalse(shield.db.worn)


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

        self.char1.at_tick.assert_called_once()
        self.char1.refresh_prompt.assert_called()
        state_manager.tick_character.assert_called_once_with(self.char1)


class TestRegeneration(EvenniaTest):
    def test_at_tick_heals_resources(self):
        char = self.char1
        for key in ("health", "mana", "stamina"):
            trait = char.traits.get(key)
            trait.current = trait.max // 2
        char.refresh_prompt = MagicMock()
        char.msg = MagicMock()

        with patch("typeclasses.characters.randint", return_value=2):
            char.at_tick()

        for key in ("health", "mana", "stamina"):
            trait = char.traits.get(key)
            self.assertGreater(trait.current, trait.max // 2)

        char.refresh_prompt.assert_called_once()
        char.msg.assert_called()
