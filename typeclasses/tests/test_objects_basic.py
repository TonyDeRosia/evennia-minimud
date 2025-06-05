from unittest.mock import MagicMock, patch

from evennia import create_object
from evennia.utils.test_resources import EvenniaTest


class TestObjectCreation(EvenniaTest):
    def test_default_weight_on_creation(self):
        obj = create_object("typeclasses.objects.Object", key="widget")
        self.assertEqual(obj.db.weight, 1)

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

