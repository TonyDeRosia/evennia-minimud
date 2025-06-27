from collections import Counter
from evennia import CmdSet
from evennia.utils import iter_to_str, make_iter
from evennia.utils.evtable import EvTable
from utils.currency import to_copper, from_copper, format_wallet

from .command import Command


class CmdList(Command):
    """
    View items a shop has for sale. Usage: list

    Usage:
        list

    See |whelp list|n for details.
    """

    key = "list"
    aliases = ("browse",)
    help_category = "Here"

    def func(self):
        # verify that this shop has a storage box
        if not (storage := self.obj.db.storage):
            self.msg("This shop is not open for business.")
            return

        listings = []
        for obj in storage.contents:
            # check if the object has a price set
            if price := obj.db.price:
                # add it and its price to the listings
                listings.append((obj.name, price))

        condensed = Counter(listings)
        listings = [[key[0], val, key[1]] for key, val in condensed.items()]
        if not condensed:
            self.msg("This shop has nothing for sale right now.")
            return

        # build a table from the sale listings
        table = EvTable("Item", "Amt", "Price", border="rows")
        for key, val in condensed.items():
            table.add_row(key[0], val, key[1])

        # send it to the player
        self.msg(str(table))


class CmdBuy(Command):
    """
    Purchase an item from a shop. Usage: buy <item>

    Usage:
        buy

    See |whelp buy|n for details.
    """

    key = "buy"
    aliases = ("order", "purchase")
    help_category = "Here"

    def parse(self):
        """
        Parse out the optional number of units for the command
        """
        self.args = self.args.strip()
        # this splits the args at the first space into a string and a possibly-empty list of strings
        first, *rest = self.args.split(" ", maxsplit=1)

        # if the rest is empty, we assume it's just an object name
        if not rest:
            self.count = 1
        # is the first item a number?
        elif first.isdecimal():
            self.count = int(first)
            # combine the rest back into a string
            self.args = " ".join(rest)
        else:
            # the first word is not a number, so it's all just one object
            self.count = 1

    def func(self):
        # verify that this shop has a storage box
        if not (storage := self.obj.db.storage):
            self.msg("This shop is not open for business.")
            return

        # we want a stack of the item, matching the parsed count
        objs = self.caller.search_first(
            self.args, location=storage, stacked=self.count
        )
        if not objs:
            # we found nothing, or it was too vague of a search
            return

        # make the result into a list so we can handle it consistently
        objs = make_iter(objs)
        objs = [obj for obj in objs if obj.db.price]
        if not objs:
            # avoid this! don't put objects without price tags into the storage box!
            self.msg(f"There are no {self.args} for sale.")
            return

        example = objs[0]
        count = len(objs)
        obj_name = example.get_numbered_name(count, self.caller)[1]
        can_buy, total = self.obj.check_purchase(self.caller, objs)
        if can_buy is False:
            self.msg(f"You need {total} coins to buy that.")
            return

        # confirm that this is what the player wants to buy
        confirm = yield (
            f"Do you want to buy {obj_name} for {total} coin{'' if total == 1 else 's'}? Yes/No"
        )

        # if it's not a form of yes, cancel
        if confirm.lower().strip() not in ("yes", "y"):
            self.msg("Purchase cancelled.")
            return

        success, spent = self.obj.purchase(self.caller, objs)
        if not success:
            self.msg(f"You need {spent} coins to buy that.")
            return

        self.msg(
            f"You exchange {spent} coin{'' if spent == 1 else 's'} for {count} {obj_name}."
        )


class CmdSell(Command):
    """
    Offer an item for sale to a shop. Usage: sell <item>

    Usage:
        sell

    See |whelp sell|n for details.
    """

    key = "sell"
    help_category = "Here"

    def parse(self):
        """
        Parse out the optional number of units for the command
        """
        self.args = self.args.strip()
        # this splits the args at the first space into a string and a possibly-empty list of strings
        first, *rest = self.args.split(" ", maxsplit=1)

        # if the rest is empty, we assume it's just an object name
        if not rest:
            self.count = 1
        # is the first item a number?
        elif first.isdecimal():
            self.count = int(first)
            # combine the rest back into a string
            self.args = " ".join(rest)
        else:
            # the first word is not a number, so it's all just one object
            self.count = 1

    def func(self):
        # verify that this shop has a storage box
        if not (storage := self.obj.db.storage):
            self.msg("This shop is not open for business.")
            return

        # we want a stack of the item, matching the parsed count
        objs = self.caller.search_first(
            self.args, location=self.caller, stacked=self.count
        )
        if not objs:
            # we found nothing, or it was too vague of a search
            return

        # make the result into a list so we can handle it consistently
        objs = make_iter(objs)
        example = objs[0]
        count = len(objs)
        obj_name = example.get_numbered_name(count, self.caller)[1]
        # calculate the total for all the objects
        total = sum([obj.attributes.get("value", 0) for obj in objs])

        # confirm that this is what the player wants to buy
        confirm = yield (
            f"Do you want to sell {obj_name} for {total} coin{'' if total == 1 else 's'}? Yes/No"
        )

        # if it's not a form of yes, cancel
        if confirm.lower().strip() not in ("yes", "y"):
            self.msg("Sale cancelled.")
            return

        # everything is good! do a capitalism!
        for obj in objs:
            self.obj.add_stock(obj)

        wallet = self.caller.db.coins or {}
        self.caller.db.coins = from_copper(to_copper(wallet) + total)

        self.msg(
            f"You exchange {obj_name} for {total} coin{'' if total == 1 else 's'}."
        )


class CmdDonate(Command):
    """
    Donate resources here in exchange for experience.

    Enter "donate" by itself to see what kinds of resources are accepted.

    Usage:
        donate [quantity] <object>

    Example:
        donate 5 apple
    """

    key = "donate"

    def parse(self):
        """
        Parse out the optional number of units for the command
        """
        self.args = self.args.strip()
        if not self.args:
            return
        # this splits the args at the first space into a string and a possibly-empty list of strings
        first, *rest = self.args.split(" ", maxsplit=1)

        # if the rest is empty, we assume it's just an object name
        if not rest:
            self.count = 1
        # is the first item a number?
        elif first.isdecimal():
            self.count = int(first)
            # combine the rest back into a string
            self.args = " ".join(rest)
        else:
            # the first word is not a number, so it's all just one object
            self.count = 1

    def func(self):
        # verify that this shop has a storage box
        if not (donations := self.obj.db.donation_tags):
            self.msg("This shop does not accept donations.")
            return

        if not self.args:
            # report back what this shop accepts
            self.msg(f"You can donate {iter_to_str(donations)} here.")
            return

        # filter possible donatable objects by the types accepted here
        candidates = [
            obj
            for obj in self.caller.contents
            if obj.tags.has(donations, category="crafting_material")
        ]

        # we want a stack of the item, matching the parsed count
        objs = self.caller.search_first(
            self.args, candidates=candidates, stacked=self.count
        )
        if not objs:
            # we found nothing, or it was too vague of a search
            return

        # make the result into a list so we can handle it consistently
        objs = make_iter(objs)
        example = objs[0]
        count = len(objs)
        obj_name = example.get_numbered_name(count, self.caller)[1]
        # calculate the total for all the objects
        total = sum([obj.attributes.get("value", 0) for obj in objs]) // 2

        # confirm that this is what the player wants to buy
        confirm = yield (
            f"Do you want to trade in {obj_name} for {total} experience? Yes/No"
        )

        # if it's not a form of yes, cancel
        if confirm.lower().strip() not in ("yes", "y"):
            self.msg("Donation cancelled.")
            return

        # everything is good! do a capitalism!
        for obj in objs:
            obj.delete()

        from world.system import state_manager
        state_manager.gain_xp(self.caller, total, announce=True)

        self.msg(f"You exchange {obj_name} for {total} experience.")


class ShopCmdSet(CmdSet):
    key = "Shop CmdSet"

    def at_cmdset_creation(self):
        super().at_cmdset_creation()

        self.add(CmdList)
        self.add(CmdBuy)
        self.add(CmdSell)
        self.add(CmdDonate)


class CmdMoney(Command):
    """
    View how many coins you have

    Usage:
        coins
    """

    key = "coins"
    aliases = ("wallet", "money")

    def func(self):
        coins = self.caller.db.coins or {}
        self.msg(f"You have {format_wallet(coins)}.")
