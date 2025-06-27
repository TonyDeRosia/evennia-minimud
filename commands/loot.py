from evennia import CmdSet
from .command import Command


class CmdLoot(Command):
    """Loot items from a corpse."""

    key = "loot"
    aliases = ("loot corpse",)
    help_category = "General"

    def func(self):
        caller = self.caller
        if not self.args:
            if self.cmdstring.strip().lower() == "loot corpse":
                corpses = [
                    obj
                    for obj in caller.location.contents
                    if obj.is_typeclass("typeclasses.objects.Corpse", exact=False)
                ]
                if not corpses:
                    caller.msg("There is nothing to loot.")
                    return
                target = corpses[0]
            else:
                caller.msg("Loot what?")
                return
        else:
            target = caller.search_first(self.args.strip())
        if not target:
            return
        if not target.is_typeclass("typeclasses.objects.Corpse", exact=False):
            caller.msg("You can only loot corpses.")
            return
        items = list(target.contents)
        if not items:
            caller.msg("There's nothing left to loot.")
            return
        for obj in items:
            if obj.move_to(caller, quiet=True, move_type="get"):
                obj.at_get(caller)
                caller.msg(
                    f"You loot {obj.get_display_name(caller)} from {target.get_display_name(caller)}."
                )
        caller.update_carry_weight()


class CmdLootCorpse(Command):
    """Loot everything from a corpse that you can pick up."""

    key = "lootcorpse"
    help_category = "General"

    def func(self):
        caller = self.caller
        if not self.args:
            caller.msg("Loot what?")
            return
        target = caller.search_first(self.args.strip())
        if not target:
            return
        if not target.is_typeclass("typeclasses.objects.Corpse", exact=False):
            caller.msg("You can only loot corpses.")
            return
        items = list(target.contents)
        if not items:
            caller.msg("There's nothing left to loot.")
            return
        moved_any = False
        for obj in items:
            if not obj.access(caller, "get"):
                continue
            if obj.move_to(caller, quiet=True, move_type="get"):
                obj.at_get(caller)
                moved_any = True
                caller.msg(
                    f"You loot {obj.get_display_name(caller)} from {target.get_display_name(caller)}."
                )
        caller.update_carry_weight()
        if not moved_any:
            caller.msg("You cannot loot anything from it.")


class LootCmdSet(CmdSet):
    key = "Loot CmdSet"

    def at_cmdset_creation(self):
        super().at_cmdset_creation()
        self.add(CmdLoot)
        self.add(CmdLootCorpse)

