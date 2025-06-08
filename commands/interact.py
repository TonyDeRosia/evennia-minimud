from .command import Command
from evennia import CmdSet
from evennia.utils import make_iter
from world.system.constants import MAX_SATED, MAX_LEVEL


class CmdGather(Command):
    """
    Collect resources from a gathering node. Usage: gather

    Usage:
        gather

    See |whelp gather|n for details.
    """

    key = "gather"
    aliases = ("collect", "harvest")
    help_category = "Here"

    def func(self):
        if not self.obj:
            return

        try:
            self.obj.at_gather(self.caller)
        except AttributeError:
            self.msg("You cannot gather anything from that.")


class GatherCmdSet(CmdSet):
    key = "Gather CmdSet"

    def at_cmdset_creation(self):
        super().at_cmdset_creation()
        # add the cmd
        self.add(CmdGather)


class CmdEat(Command):
    """
    Eat or drink something edible.

    Usage:
        eat <item>

    Example:
        eat apple
    """

    key = "eat"
    aliases = ("drink", "consume", "devour", "chug", "quaff")

    def func(self):
        caller = self.caller
        obj = caller.search(self.args.strip(), stacked=1)
        if not obj:
            return
        # stacked sometimes returns a list, so make sure it is one for consistent handling
        obj = make_iter(obj)[0]

        is_admin = caller.check_permstring("Admin") or caller.check_permstring("Builder")

        if self.cmdstring == "quaff" and not getattr(obj.db, "is_potion", False):
            caller.msg("You can only quaff potions.")
            return

        if not obj.tags.has("edible") and not is_admin:
            caller.msg("You cannot eat that.")
            return

        if obj in caller.equipment.values():
            caller.msg("You must unequip that first.")
            return

        stamina = obj.attributes.get("stamina", 0)
        caller.traits.stamina.current += stamina

        sated = obj.attributes.get("sated", 0)
        if (caller.db.level or 1) < MAX_LEVEL:
            caller.db.sated = min((caller.db.sated or 0) + sated, MAX_SATED)

        caller.at_emote(
            f"$conj({self.cmdstring}) the {{target}}.", mapping={"target": obj}
        )
        if sated:
            caller.msg(f"(Sated +{sated})")
        obj.delete()


class InteractCmdSet(CmdSet):
    key = "Interact CmdSet"

    def at_cmdset_creation(self):
        super().at_cmdset_creation()
        self.add(CmdEat)
