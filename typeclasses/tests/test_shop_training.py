from unittest.mock import patch

from evennia.utils import create
from evennia.utils.test_resources import EvenniaTest
from django.conf import settings

from utils.currency import from_copper, to_copper
from evennia.prototypes.prototypes import PROTOTYPE_TAG_CATEGORY


class TestShopRestock(EvenniaTest):
    def setUp(self):
        super().setUp()
        if "world.prototypes" not in settings.PROTOTYPE_MODULES:
            settings.PROTOTYPE_MODULES.append("world.prototypes")

    @patch("typeclasses.scripts.randint", return_value=1)
    def test_restock_adds_stock(self, mock_rand):
        from typeclasses.rooms import XYGridShop

        shop = create.create_object(XYGridShop, key="shop")
        shop.db.inventory = [("IRON_DAGGER", 1)]
        script = shop.scripts.get("restock")[0]
        script.at_repeat()

        storage = shop.db.storage
        self.assertEqual(len(storage.contents), 1)
        item = storage.contents[0]
        self.assertTrue(item.tags.has("IRON_DAGGER", category=PROTOTYPE_TAG_CATEGORY))
        self.assertEqual(item.db.price, item.db.value * 2)

    @patch("typeclasses.scripts.randint", return_value=1)
    def test_purchase_spends_coins(self, mock_rand):
        from typeclasses.rooms import XYGridShop

        shop = create.create_object(XYGridShop, key="shop2")
        shop.db.inventory = [("IRON_DAGGER", 1)]
        script = shop.scripts.get("restock")[0]
        script.at_repeat()
        item = shop.db.storage.contents[0]

        self.char1.db.coins = from_copper(item.db.price)
        ok, cost = shop.purchase(self.char1, [item])

        self.assertTrue(ok)
        self.assertEqual(to_copper(self.char1.db.coins), 0)
        self.assertIn(item, self.char1.contents)


class TestTraining(EvenniaTest):
    def test_train_skill_costs_xp(self):
        from typeclasses.rooms import XYGridTrain

        trainer = create.create_object(XYGridTrain, key="dojo")
        trainer.db.skill_training = "smithing"
        self.char1.db.exp = 10

        success, cost, new_level = trainer.train_skill(self.char1, 2)

        self.assertTrue(success)
        self.assertEqual(cost, 3)
        self.assertEqual(new_level, 2)
        self.assertEqual(self.char1.db.exp, 7)
