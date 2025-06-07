from unittest.mock import MagicMock
from evennia.utils.test_resources import EvenniaTest
from evennia.utils import create
from utils.currency import from_copper, to_copper


class TestMerchantTrading(EvenniaTest):
    def setUp(self):
        super().setUp()
        from typeclasses.npcs import Merchant
        self.merchant = create.create_object(Merchant, key="shopkeep", location=self.room1)
        self.char1.db.coins = from_copper(20)
        self.merchant.db.coins = from_copper(0)
        item = create.create_object("typeclasses.objects.Object", key="gem", location=self.merchant.db.storage)
        item.db.price = 10
        item.db.value = 5
        self.item = item
        self.char1.msg = MagicMock()
        self.merchant.msg = MagicMock()

    def test_buy_transfers_coins(self):
        self.char1.execute_cmd("buy gem")
        self.assertEqual(to_copper(self.char1.db.coins), 10)
        self.assertEqual(to_copper(self.merchant.db.coins), 10)
        self.assertEqual(self.item.location, self.char1)

    def test_sell_transfers_coins(self):
        obj = create.create_object("typeclasses.objects.Object", key="rock", location=self.char1)
        obj.db.value = 4
        self.char1.execute_cmd("sell rock")
        self.assertEqual(to_copper(self.char1.db.coins), 24)
        self.assertEqual(to_copper(self.merchant.db.coins), 4)

