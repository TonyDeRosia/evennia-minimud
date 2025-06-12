from evennia.utils.evmenu import EvMenu
from utils.prototype_manager import load_prototype, save_prototype
from .command import Command


def menunode_vnum(caller, raw_string="", **kwargs):
    text = "|wEnter room vnum|n"
    options = {"key": "_default", "goto": _set_vnum}
    return text, options


def _set_vnum(caller, raw_string, **kwargs):
    val = raw_string.strip()
    if not val.isdigit():
        caller.msg("Enter a numeric vnum.")
        return "menunode_vnum"
    caller.ndb.rp_vnum = int(val)
    return "menunode_trigger"


def menunode_trigger(caller, raw_string="", **kwargs):
    text = "|wEnter trigger type|n"
    options = {"key": "_default", "goto": _set_trigger}
    return text, options


def _set_trigger(caller, raw_string, **kwargs):
    trig = raw_string.strip()
    if not trig:
        caller.msg("Enter a trigger type.")
        return "menunode_trigger"
    caller.ndb.rp_trigger = trig
    return "menunode_command"


def menunode_command(caller, raw_string="", **kwargs):
    text = "|wEnter command string|n"
    options = {"key": "_default", "goto": _save_prog}
    return text, options


def _save_prog(caller, raw_string, **kwargs):
    cmd = raw_string.strip()
    if not cmd:
        caller.msg("Enter a command string.")
        return "menunode_command"
    vnum = caller.ndb.rp_vnum
    trigger = caller.ndb.rp_trigger
    proto = load_prototype("room", vnum)
    if proto is None:
        caller.msg("Prototype not found.")
        return None
    progs = proto.setdefault("roomprogs", [])
    progs.append({"type": trigger, "commands": [cmd]})
    save_prototype("room", proto, vnum=vnum)
    caller.msg("Room program saved.")
    caller.ndb.rp_vnum = None
    caller.ndb.rp_trigger = None
    return None


class CmdRPEdit(Command):
    """Attach a program to a room prototype."""

    key = "rpedit"
    locks = "cmd:perm(Builder)"
    help_category = "Building"

    def func(self):
        start = "menunode_vnum"
        if self.args.strip().isdigit():
            self.caller.ndb.rp_vnum = int(self.args.strip())
            start = "menunode_trigger"
        EvMenu(self.caller, "commands.rpedit", startnode=start)

