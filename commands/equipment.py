from evennia import CmdSet
from evennia.utils.ansi import strip_ansi
from .command import Command


def match_name(obj, name):
    """Return True if obj.key matches name ignoring ANSI."""
    return strip_ansi(obj.key).lower() == name.lower()


def get_equipped_item_by_name(caller, itemname):
    """Find equipped item by name."""
    eq = caller.equipment
    for slot, item in eq.items():
        if item and match_name(item, itemname):
            return slot, item
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


class EquipmentCmdSet(CmdSet):
    key = "Equipment CmdSet"

    def at_cmdset_creation(self):
        super().at_cmdset_creation()
        self.add(CmdRemove)
