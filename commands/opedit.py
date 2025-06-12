from evennia.utils.evmenu import EvMenu
from utils.prototype_manager import load_prototype, save_prototype
from .command import Command


def menunode_vnum(caller, raw_string="", **kwargs):
    text = "|wEnter object vnum|n"
    options = {"key": "_default", "goto": _set_vnum}
    return text, options


def _set_vnum(caller, raw_string, **kwargs):
    val = raw_string.strip()
    if not val.isdigit():
        caller.msg("Enter a numeric vnum.")
        return "menunode_vnum"
    caller.ndb.op_vnum = int(val)
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
    caller.ndb.op_trigger = trig
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
    vnum = caller.ndb.op_vnum
    trigger = caller.ndb.op_trigger
    proto = load_prototype("object", vnum)
    if proto is None:
        caller.msg("Prototype not found.")
        return None
    progs = proto.setdefault("objprogs", [])
    progs.append({"type": trigger, "commands": [cmd]})
    save_prototype("object", proto, vnum=vnum)
    caller.msg("Object program saved.")
    caller.ndb.op_vnum = None
    caller.ndb.op_trigger = None
    return None


class CmdOPEdit(Command):
    """Attach a program to an object prototype."""

    key = "opedit"
    locks = "cmd:perm(Builder)"
    help_category = "Building"

    def func(self):
        start = "menunode_vnum"
        if self.args.strip().isdigit():
            self.caller.ndb.op_vnum = int(self.args.strip())
            start = "menunode_trigger"
        EvMenu(self.caller, "commands.opedit", startnode=start)

