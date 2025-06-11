from evennia.utils.evmenu import EvMenu
from utils.prototype_manager import load_prototype
from utils.vnum_registry import validate_vnum, register_vnum
from .command import Command
from . import npc_builder


class CmdMEdit(Command):
    """Reopen the CNPC builder for the given prototype VNUM."""

    key = "medit"
    locks = "cmd:perm(Builder)"
    help_category = "Building"

    def func(self):
        caller = self.caller
        if not self.args or not self.args.strip().isdigit():
            caller.msg("Usage: medit <vnum>")
            return
        vnum = int(self.args.strip())
        proto = load_prototype("npc", vnum)
        if proto is None:
            if not validate_vnum(vnum, "npc"):
                caller.msg("Invalid or already used VNUM.")
                return
            register_vnum(vnum)
            proto = {"key": f"mob_{vnum}", "level": 1}
        caller.ndb.mob_vnum = vnum
        caller.ndb.buildnpc = dict(proto)
        EvMenu(
            caller,
            "commands.npc_builder",
            startnode="menunode_desc",
            cmd_on_exit=npc_builder._on_menu_exit,
        )
