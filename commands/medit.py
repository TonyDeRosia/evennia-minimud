from evennia.utils.evmenu import EvMenu
from utils.prototype_manager import load_prototype
from utils.vnum_registry import validate_vnum, register_vnum
from utils.mob_proto import get_prototype
from .command import Command
from . import npc_builder
from world.templates.mob_templates import get_template


class CmdMEdit(Command):
    """Reopen the CNPC builder for the given prototype VNUM."""

    key = "medit"
    locks = "cmd:perm(Builder)"
    help_category = "Building"

    def func(self):
        caller = self.caller
        args = self.args.strip()
        if not args:
            caller.msg("Usage: medit <vnum> | medit create <vnum>")
            return

        parts = args.split(None, 1)
        sub = parts[0].lower()

        if sub == "create":
            if len(parts) != 2 or not parts[1].isdigit():
                caller.msg("Usage: medit create <vnum>")
                return
            vnum = int(parts[1])
            if not validate_vnum(vnum, "npc"):
                caller.msg("Invalid or already used VNUM.")
                return
            register_vnum(vnum)
            proto = get_template("warrior") or {}
            proto.setdefault("key", f"mob_{vnum}")
            proto.setdefault("level", 1)
            proto["vnum"] = vnum
        else:
            if not sub.isdigit():
                caller.msg("Usage: medit <vnum> | medit create <vnum>")
                return
            vnum = int(sub)
            proto = get_prototype(vnum)
            if proto is None:
                proto = load_prototype("npc", vnum)
            if proto is None:
                if not validate_vnum(vnum, "npc"):
                    caller.msg("Invalid or already used VNUM.")
                    return
                register_vnum(vnum)
                proto = {"key": f"mob_{vnum}", "level": 1}
            proto.setdefault("vnum", vnum)

        caller.ndb.mob_vnum = vnum
        caller.ndb.buildnpc = dict(proto)
        caller.ndb.buildnpc_orig = dict(caller.ndb.buildnpc)
        startnode = "menunode_desc" if caller.ndb.buildnpc.get("key") else "menunode_key"
        EvMenu(
            caller,
            "world.menus.mob_builder_menu",
            startnode=startnode,
            cmd_on_exit=npc_builder._on_menu_exit,
        )
