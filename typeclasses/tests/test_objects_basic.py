from unittest.mock import MagicMock, patch

from evennia import create_object
from evennia.utils.test_resources import EvenniaTest


class TestObjectCreation(EvenniaTest):
    def test_default_weight_on_creation(self):
        obj = create_object("typeclasses.objects.Object", key="widget")
        self.assertEqual(obj.db.weight, 0)

    def test_weight_not_overwritten(self):
        obj = create_object("typeclasses.objects.Object", key="stone")
        obj.db.weight = 5
        obj.at_object_creation()
        self.assertEqual(obj.db.weight, 5)


class TestObjectFlags(EvenniaTest):
    def test_stationary_blocks_move(self):
        obj = create_object("typeclasses.objects.Object", key="rock")
        obj.tags.add("stationary", category="flag")
        mover = self.char1
        mover.msg = MagicMock()
        result = obj.at_pre_move(self.room2, caller=mover)
        self.assertFalse(result)
        mover.msg.assert_called_with(f"{obj.get_display_name(mover)} refuses to budge.")

    @patch("typeclasses.objects.ContribClothing.wear")
    def test_wear_requires_flags(self, mock_wear):
        item = create_object("typeclasses.objects.ClothingObject", key="cloak", location=self.char1)
        self.char1.msg = MagicMock()

        # Missing equipment flag
        item.tags.add("identified", category="flag")
        item.wear(self.char1, "wear")
        self.char1.msg.assert_called_with(f"{item.get_display_name(self.char1)} can't be worn.")
        mock_wear.assert_not_called()
        self.char1.msg.reset_mock()

        # Missing identified flag
        item.tags.add("equipment", category="flag")
        item.tags.remove("identified", category="flag")
        item.wear(self.char1, "wear")
        self.char1.msg.assert_called_with(f"You don't know how to use {item.get_display_name(self.char1)}.")
        mock_wear.assert_not_called()
        self.char1.msg.reset_mock()

        # Has both flags
        item.tags.add("identified", category="flag")
        item.wear(self.char1, "wear")
        mock_wear.assert_called()

    def test_wear_replaces_existing(self):
        first = create_object(
            "typeclasses.objects.ClothingObject",
            key="hat1",
            location=self.char1,
        )
        first.tags.add("equipment", category="flag")
        first.tags.add("identified", category="flag")
        first.tags.add("head", category="slot")

        second = create_object(
            "typeclasses.objects.ClothingObject",
            key="hat2",
            location=self.char1,
        )
        second.tags.add("equipment", category="flag")
        second.tags.add("identified", category="flag")
        second.tags.add("head", category="slot")

        first.wear(self.char1, "wear")
        self.assertTrue(first.db.worn)

        second.wear(self.char1, "wear")
        self.assertTrue(second.db.worn)
        self.assertFalse(first.db.worn)
        self.assertEqual(first.location, self.char1)

    def test_wear_adds_canonical_slot_tag(self):
        item = create_object(
            "typeclasses.objects.ClothingObject",
            key="ring",
            location=self.char1,
        )
        item.tags.add("equipment", category="flag")
        item.tags.add("identified", category="flag")
        item.tags.add("ring", category="slot")

        item.wear(self.char1, True)
        self.assertTrue(item.tags.has("ring1", category="slot"))


class TestInspectFlags(EvenniaTest):
    def test_inspect_shows_flags(self):
        obj = self.obj1
        obj.db.desc = "A shiny object."
        obj.db.identified = True
        obj.tags.add("equipment", category="flag")
        obj.tags.add("rare", category="flag")
        self.char1.msg = MagicMock()
        self.char1.execute_cmd(f"inspect {obj.key}")
        out = self.char1.msg.call_args[0][0]
        self.assertIn("Flags: equipment, rare", out)


class TestMeleeWeaponUtility(EvenniaTest):
    def test_is_twohanded_attribute(self):
        weapon = create_object(
            "typeclasses.gear.MeleeWeapon",
            key="great",
            location=self.char1,
            nohome=True,
        )
        weapon.db.twohanded = True
        self.assertTrue(weapon.is_twohanded())

    def test_is_twohanded_flag_tag(self):
        weapon = create_object(
            "typeclasses.gear.MeleeWeapon",
            key="axe",
            location=self.char1,
            nohome=True,
        )
        weapon.tags.add("twohanded", category="flag")
        self.assertTrue(weapon.is_twohanded())

    def test_is_twohanded_wielded_tag(self):
        weapon = create_object(
            "typeclasses.gear.MeleeWeapon",
            key="spear",
            location=self.char1,
            nohome=True,
        )
        weapon.tags.add("two_handed", category="wielded")
        self.assertTrue(weapon.is_twohanded())

    def test_is_twohanded_false(self):
        weapon = create_object(
            "typeclasses.gear.MeleeWeapon",
            key="sword",
            location=self.char1,
            nohome=True,
        )
        self.assertFalse(weapon.is_twohanded())

