from evennia.utils.evmenu import EvMenu
from .command import Command

# simple storage for created programs {vnum: [{"trigger": str, "command": str}]}
MOB_PROGRAMS = {}


def menunode_vnum(caller, raw_string="", **kwargs):
    """Prompt for a mob vnum."""
    text = "|wEnter mob vnum|n"
    options = {"key": "_default", "goto": _set_vnum}
    return text, options


def _set_vnum(caller, raw_string, **kwargs):
    val = raw_string.strip()
    if not val.isdigit():
        caller.msg("Enter a numeric vnum.")
        return "menunode_vnum"
    caller.ndb.mp_vnum = int(val)
    return "menunode_trigger"


def menunode_trigger(caller, raw_string="", **kwargs):
    """Prompt for trigger type."""
    text = "|wEnter trigger type|n"
    options = {"key": "_default", "goto": _set_trigger}
    return text, options


def _set_trigger(caller, raw_string, **kwargs):
    trig = raw_string.strip()
    if not trig:
        caller.msg("Enter a trigger type.")
        return "menunode_trigger"
    caller.ndb.mp_trigger = trig
    return "menunode_command"


def menunode_command(caller, raw_string="", **kwargs):
    """Prompt for command string."""
    text = "|wEnter command string|n"
    options = {"key": "_default", "goto": _save_prog}
    return text, options


def _save_prog(caller, raw_string, **kwargs):
    cmd = raw_string.strip()
    if not cmd:
        caller.msg("Enter a command string.")
        return "menunode_command"
    vnum = caller.ndb.mp_vnum
    trigger = caller.ndb.mp_trigger
    progs = MOB_PROGRAMS.setdefault(vnum, [])
    progs.append({"trigger": trigger, "command": cmd})
    caller.msg("Mob program saved.")
    caller.ndb.mp_vnum = None
    caller.ndb.mp_trigger = None
    return None


class CmdMPEdit(Command):
    """Create a simple mob program."""

    key = "mpedit"
    locks = "cmd:perm(Builder)"
    help_category = "Building"

    def func(self):
        start = "menunode_vnum"
        if self.args.strip().isdigit():
            self.caller.ndb.mp_vnum = int(self.args.strip())
            start = "menunode_trigger"
        EvMenu(self.caller, "commands.mpedit", startnode=start)
