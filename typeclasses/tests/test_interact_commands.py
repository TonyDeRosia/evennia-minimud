from unittest.mock import MagicMock

from evennia import create_object
from evennia.utils.test_resources import EvenniaTest
from django.test import override_settings
from typeclasses.objects import Object
from commands.interact import InteractCmdSet


@override_settings(DEFAULT_HOME=None)
class TestInteractCommands(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.char1.msg = MagicMock()
        self.char1.cmdset.add_default(InteractCmdSet)

    def _make_food(self, key="food", is_potion=False):
        obj = create_object(Object, key=key, location=self.char1.location)
        obj.tags.add("edible")
        obj.db.stamina = 2
        obj.db.sated = 3
        if is_potion:
            obj.db.is_potion = True
        return obj

    def test_eat_consumes_and_restores(self):
        food = self._make_food()
        stam = self.char1.traits.stamina.current
        sated = self.char1.db.sated or 0
        self.char1.execute_cmd(f"eat {food.key}")
        self.assertIsNone(food.pk)
        self.assertEqual(self.char1.traits.stamina.current, stam + 2)
        self.assertEqual(self.char1.db.sated, sated + 3)

    def test_quaff_requires_potion(self):
        drink = self._make_food(key="water")
        self.char1.execute_cmd("quaff water")
        self.char1.msg.assert_called_with("You can only quaff potions.")
        self.assertIsNotNone(drink.pk)

    def test_quaff_consumes_potion(self):
        potion = self._make_food(key="potion", is_potion=True)
        stam = self.char1.traits.stamina.current
        sated = self.char1.db.sated or 0
        self.char1.execute_cmd("quaff potion")
        self.assertIsNone(potion.pk)
        self.assertEqual(self.char1.traits.stamina.current, stam + 2)
        self.assertEqual(self.char1.db.sated, sated + 3)
