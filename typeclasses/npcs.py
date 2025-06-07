from evennia import AttributeProperty
from evennia.utils import create

from .characters import NPC
from commands.shops import MerchantCmdSet


class Merchant(NPC):
    """An NPC that buys and sells items."""

    merchant = AttributeProperty(True)
    merchant_type = AttributeProperty("")
    buy_markup = AttributeProperty(2)
    sell_discount = AttributeProperty(1)

    def at_object_creation(self):
        super().at_object_creation()
        self.cmdset.add(MerchantCmdSet, persistent=True)
        if not self.db.storage:
            self.db.storage = create.object(
                key=f"{self.key} storage",
                locks="view:perm(Builder);get:perm(Builder);search:perm(Builder)",
                home=self,
                location=self,
            )

    @property
    def shop_inventory(self):
        storage = self.db.storage or self
        return [obj for obj in storage.contents if obj.db.price]

    def add_stock(self, obj):
        storage = self.db.storage or self
        obj.location = storage
        val = obj.db.value or 0
        markup = self.db.buy_markup or 1
        obj.db.price = int(val * markup)
        return True

    def at_object_receive(self, obj, source_location, **kwargs):
        super().at_object_receive(obj, source_location, **kwargs)
        if source_location and source_location.has_account:
            self.add_stock(obj)

from commands.banking import BankCmdSet


class Banker(NPC):
    """NPC that manages player bank accounts."""

    banker = AttributeProperty(True)

    def at_object_creation(self):
        super().at_object_creation()
        self.cmdset.add(BankCmdSet, persistent=True)

