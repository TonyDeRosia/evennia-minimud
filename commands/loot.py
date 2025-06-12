from evennia import CmdSet
from .command import Command


class CmdLoot(Command):
    """Loot items from a corpse."""

    key = "loot"
    help_category = "General"

    def func(self):
        caller = self.caller
        if not self.args:
            caller.msg("Loot what?")
            return
        target = caller.search(self.args.strip())
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


class LootCmdSet(CmdSet):
    key = "Loot CmdSet"

    def at_cmdset_creation(self):
        super().at_cmdset_creation()
        self.add(CmdLoot)
