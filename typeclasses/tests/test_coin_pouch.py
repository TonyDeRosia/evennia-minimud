from unittest.mock import MagicMock

from evennia.utils.test_resources import EvenniaTest
from django.test import override_settings
from utils.currency import from_copper, to_copper


@override_settings(DEFAULT_HOME=None)
class TestCoinPouchCoins(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.char1.msg = MagicMock()
        self.char2.msg = MagicMock()

    def test_pouch_coins_auto_deposit(self):
        self.char1.db.coins = from_copper(20)
        self.char1.execute_cmd("drop 5 copper")

        coin = next(
            obj
            for obj in self.char1.location.contents
            if obj.is_typeclass("typeclasses.objects.CoinPile", exact=False)
        )
        self.assertTrue(coin.db.from_pouch)
        self.assertEqual(to_copper(self.char1.db.coins), 15)

        self.char1.msg.reset_mock()
        self.char1.execute_cmd("get copper coins")

        self.assertEqual(to_copper(self.char1.db.coins), 20)
        self.assertIsNone(coin.pk)
        self.char1.msg.assert_any_call("You receive |Y5 copper coins|n.")

    def test_give_coins_auto_deposit(self):
        self.char1.db.coins = from_copper(10)
        self.char2.db.coins = from_copper(0)

        self.char1.execute_cmd(f"give 5 copper={self.char2.key}")

        self.assertEqual(to_copper(self.char1.db.coins), 5)
        self.assertEqual(to_copper(self.char2.db.coins), 5)

        # coin pile object should have been cleaned up
        piles = [
            obj
            for obj in self.char2.contents
            if obj.is_typeclass("typeclasses.objects.CoinPile", exact=False)
        ]
        self.assertFalse(piles)

        self.char2.msg.assert_any_call("You receive |Y5 copper coins|n.")

    def test_getall_auto_deposit(self):
        self.char1.db.coins = from_copper(30)
        self.char1.execute_cmd("drop 10 copper")

        coin = next(
            obj
            for obj in self.char1.location.contents
            if obj.is_typeclass("typeclasses.objects.CoinPile", exact=False)
        )

        self.char1.msg.reset_mock()
        self.char1.execute_cmd("get all")

        self.assertEqual(to_copper(self.char1.db.coins), 30)
        self.assertIsNone(coin.pk)
        self.char1.msg.assert_any_call("You receive |Y10 copper coins|n.")

