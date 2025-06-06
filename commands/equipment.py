from evennia import CmdSet
from evennia.contrib.game_systems.clothing.clothing import get_worn_clothes
from .command import Command


class CmdRemove(Command):
    """Remove a worn item and return it to inventory."""

    key = "remove"
    aliases = ("takeoff",)
    help_category = "General"

    def func(self):
        caller = self.caller
        if not self.args:
            caller.msg("Remove what?")
            return

        candidates = list(get_worn_clothes(caller))
        # include worn items still in inventory
        candidates.extend(o for o in caller.contents if getattr(o.db, "worn", False))
        obj = caller.search(self.args.strip(), candidates=candidates)
        if not obj:
            return
        obj.remove(caller)


class EquipmentCmdSet(CmdSet):
    key = "Equipment CmdSet"

    def at_cmdset_creation(self):
        super().at_cmdset_creation()
        self.add(CmdRemove)
