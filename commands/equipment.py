from evennia import CmdSet
from evennia.utils.ansi import strip_ansi
from .command import Command


def get_equipped_item_by_name(caller, itemname):
    """Find equipped item by name."""
    eq = caller.equipment
    candidates = [item for item in eq.values() if item]
    searchstr = strip_ansi(itemname)
    obj = caller.search(searchstr, candidates=candidates)
    if not obj:
        return None, None
    for slot, item in eq.items():
        if item == obj:
            return slot, obj
    return None, None


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

        itemname = self.args.strip()

        # search equipped items (worn or wielded)
        slot, obj = get_equipped_item_by_name(caller, itemname)
        if not obj:
            caller.msg(f"Could not find '{itemname}'.")
            return

        if obj in caller.wielding:
            caller.at_unwield(obj)
        else:
            obj.remove(caller)

        caller.msg(f"You remove {obj.key}.")


class CmdRemoveAll(Command):
    """Remove all equipped items and return them to inventory."""

    key = "remove all"
    aliases = ("takeoff all", "removeall", "takeoffall")
    help_category = "General"

    def func(self):
        caller = self.caller
        eq = [item for item in caller.equipment.values() if item]
        if not eq:
            caller.msg("You are not wearing or wielding anything.")
            return
        for item in list(eq):
            if item in caller.wielding:
                caller.at_unwield(item)
            else:
                item.remove(caller)
            caller.msg(f"You remove {item.key}.")


class EquipmentCmdSet(CmdSet):
    key = "Equipment CmdSet"

    def at_cmdset_creation(self):
        super().at_cmdset_creation()
        self.add(CmdRemove)
        self.add(CmdRemoveAll)
