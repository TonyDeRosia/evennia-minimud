"""Tests for the bank command."""

from unittest.mock import MagicMock

from django.test import override_settings
from evennia.utils.test_resources import EvenniaTest
from utils.currency import from_copper, to_copper


@override_settings(DEFAULT_HOME=None)
class TestCmdBank(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.char1.msg = MagicMock()
        self.char2.msg = MagicMock()

    def test_deposit(self):
        self.char1.db.coins = from_copper(30)

        self.char1.execute_cmd("bank deposit 10")

        self.assertEqual(to_copper(self.char1.db.coins), 20)
        self.assertEqual(self.char1.db.bank, 10)
        self.char1.msg.assert_any_call("You deposit 10 coins into your account.")

    def test_withdraw(self):
        self.char1.db.coins = from_copper(5)
        self.char1.db.bank = 15

        self.char1.execute_cmd("bank withdraw 10")

        self.assertEqual(to_copper(self.char1.db.coins), 15)
        self.assertEqual(self.char1.db.bank, 5)
        self.char1.msg.assert_any_call("You withdraw 10 coins from your account.")

    def test_transfer(self):
        self.char1.db.bank = 20
        self.char2.db.bank = 5

        self.char1.execute_cmd(f"bank transfer 12 {self.char2.key}")

        self.assertEqual(self.char1.db.bank, 8)
        self.assertEqual(self.char2.db.bank, 17)
        self.char1.msg.assert_any_call(
            f"You transfer 12 coins to {self.char2.get_display_name(self.char1)}."
        )
        self.char2.msg.assert_any_call(
            f"{self.char1.get_display_name(self.char2)} transfers 12 coins to your account."
        )

    def test_balance(self):
        self.char1.db.coins = from_copper(22)
        self.char1.db.bank = 5

        self.char1.execute_cmd("bank balance")

        self.char1.msg.assert_any_call(
            "You have 22 Copper on hand and 5 coins in the bank."
        )

