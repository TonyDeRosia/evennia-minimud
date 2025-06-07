from unittest.mock import MagicMock
from evennia.utils.test_resources import EvenniaTest
from evennia.utils import create


class TestBanker(EvenniaTest):
    def setUp(self):
        super().setUp()
        from typeclasses.npcs import Banker
        self.banker = create.create_object(Banker, key="banker", location=self.room1)
        self.char1.msg = MagicMock()

    def test_deposit_and_withdraw(self):
        self.char1.db.coins = {"gold": 2, "silver": 5}
        self.char1.execute_cmd("deposit 1 gold")
        self.assertEqual(self.char1.db.bank.get("gold"), 1)
        self.assertEqual(self.char1.db.coins.get("gold"), 1)
        self.char1.execute_cmd("withdraw 1 gold")
        self.assertEqual(self.char1.db.bank.get("gold", 0), 0)
        self.assertEqual(self.char1.db.coins.get("gold"), 2)

    def test_multiple_currencies(self):
        self.char1.db.coins = {"copper": 10, "silver": 2}
        self.char1.execute_cmd("deposit 5 copper")
        self.char1.execute_cmd("deposit 1 silver")
        self.assertEqual(self.char1.db.bank.get("copper"), 5)
        self.assertEqual(self.char1.db.bank.get("silver"), 1)
        self.char1.execute_cmd("withdraw 1 copper")
        self.assertEqual(self.char1.db.bank.get("copper"), 4)
        self.assertEqual(self.char1.db.coins.get("copper"), 6)
