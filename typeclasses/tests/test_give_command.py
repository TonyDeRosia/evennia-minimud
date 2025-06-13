from unittest.mock import MagicMock

from evennia import create_object
from evennia.utils.test_resources import EvenniaTest
from django.test import override_settings


@override_settings(DEFAULT_HOME=None)
class TestGiveCommand(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.char1.msg = MagicMock()
        self.char2.msg = MagicMock()

    def _create_item(self, name="sword"):
        return create_object("typeclasses.objects.Object", key=name, location=self.char1)

    def test_give_item_no_equals(self):
        item = self._create_item("sword")
        self.char1.execute_cmd(f"give sword {self.char2.key}")
        self.assertEqual(item.location, self.char2)

    def test_give_coins_no_equals(self):
        from utils.currency import from_copper, to_copper, COIN_VALUES

        self.char1.db.coins = from_copper(10 * COIN_VALUES["gold"])
        self.char2.db.coins = from_copper(0)

        self.char1.execute_cmd(f"give 10 gold {self.char2.key}")

        self.assertEqual(to_copper(self.char1.db.coins), 0)
        self.assertEqual(to_copper(self.char2.db.coins), 10 * COIN_VALUES["gold"])

    def test_give_item_equals_syntax(self):
        item = self._create_item("sword")
        self.char1.execute_cmd(f"give sword={self.char2.key}")
        self.assertEqual(item.location, self.char2)
