from unittest.mock import MagicMock

from evennia.utils.test_resources import EvenniaTest
from django.test import override_settings

from commands.admin import BuilderCmdSet
from commands.interact import InteractCmdSet


@override_settings(DEFAULT_HOME=None)
class TestConsumableCommands(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.char1.msg = MagicMock()
        self.char1.cmdset.add_default(InteractCmdSet)
        self.char1.cmdset.add_default(BuilderCmdSet)

    def _find(self, key):
        for obj in self.char1.contents:
            if obj.key.lower() == key.lower():
                return obj
        return None

    def test_cfood_create_and_eat(self):
        self.char1.execute_cmd("cfood apple 4 tasty")
        food = self._find("apple")
        self.assertIsNotNone(food)
        self.assertTrue(food.tags.has("edible"))
        self.assertEqual(food.db.item_type, "food")
        self.assertEqual(food.db.type, "food")
        self.assertEqual(food.db.sated, 4)
        self.assertEqual(food.db.sated_boost, 4)
        self.assertEqual(food.db.weight, 1)
        self.assertTrue(food.db.identified)
        self.assertEqual(food.db.desc, "tasty")

        before = self.char1.db.sated or 0
        self.char1.msg.reset_mock()
        self.char1.execute_cmd("eat apple")
        self.assertIsNone(food.pk)
        self.assertEqual(self.char1.db.sated, before + 4)
        out = "".join(call.args[0] for call in self.char1.msg.call_args_list)
        self.assertIn("(Sated +4)", out)

    def test_cdrink_create_and_drink(self):
        self.char1.execute_cmd("cdrink water 2 clear")
        drink = self._find("water")
        self.assertIsNotNone(drink)
        self.assertTrue(drink.tags.has("edible"))
        self.assertEqual(drink.db.item_type, "drink")
        self.assertEqual(drink.db.sated, 2)
        self.assertEqual(drink.db.desc, "clear")

        before = self.char1.db.sated or 0
        self.char1.execute_cmd("drink water")
        self.assertIsNone(drink.pk)
        self.assertEqual(self.char1.db.sated, before + 2)

    def test_cpotion_create_and_quaff(self):
        self.char1.execute_cmd("cpotion elixir STR+1, HP+5 magic")
        potion = self._find("elixir")
        self.assertIsNotNone(potion)
        self.assertTrue(potion.tags.has("edible"))
        self.assertEqual(potion.db.item_type, "drink")
        self.assertTrue(potion.db.is_potion)
        self.assertEqual(potion.db.buffs, {"STR": 1, "HP": 5})

        before = self.char1.db.sated or 0
        self.char1.execute_cmd("quaff elixir")
        self.assertIsNone(potion.pk)
        self.assertEqual(self.char1.db.sated, before)

    def test_inspect_food(self):
        self.char1.execute_cmd("cfood cake 5 yummy")
        self.char1.msg.reset_mock()
        self.char1.execute_cmd("inspect cake")
        out = self.char1.msg.call_args[0][0]
        self.assertIn("[ ITEM INFO ]", out)
        self.assertIn("Type", out)
        self.assertIn("Food", out)
        self.assertIn("Sated Boost", out)
        self.assertIn("+5", out)
        self.assertIn("Weight", out)
        self.assertIn("Identified: yes", out)

