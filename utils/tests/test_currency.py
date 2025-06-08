"""Tests for currency conversion utilities."""

from evennia.utils.test_resources import EvenniaTest

from utils.currency import from_copper, to_copper


class TestCurrencyConversion(EvenniaTest):
    """Ensure from_copper and to_copper are inverses."""

    def test_round_trip_values(self):
        amounts = [0, 50, 123456]
        for amount in amounts:
            wallet = from_copper(amount)
            self.assertEqual(to_copper(wallet), amount)
            self.assertEqual(from_copper(to_copper(wallet)), wallet)
