# Object prototype editor

from olc.base import OLCEditor, OLCState, OLCValidator
from utils.prototype_manager import (
    load_prototype,
    save_prototype,
    load_all_prototypes,
)
from utils.vnum_registry import validate_vnum, register_vnum
from .command import Command
from commands.admin import parse_stat_mods
from utils import VALID_SLOTS, normalize_slot


# ------------------------------------------------------------
# Helper functions
# ------------------------------------------------------------

def _summary(caller) -> str:
    proto = caller.ndb.obj_proto or {}
    vnum = caller.ndb.obj_vnum
    lines = [f"|wEditing object {vnum}|n"]
    if key := proto.get("key"):
        lines.append(f"Name: {key}")
    if tclass := proto.get("typeclass"):
        lines.append(f"Typeclass: {tclass}")
    if slot := proto.get("slot"):
        lines.append(f"Wear: {slot}")
    if flags := proto.get("flags"):
        lines.append("Flags: " + ", ".join(flags))
    if mods := proto.get("stat_mods"):
        modstr = ", ".join(f"{k}+{v}" for k, v in mods.items())
        lines.append(f"Applies: {modstr}")
    return "\n".join(lines)


def _with_summary(caller, text: str) -> str:
    return f"{_summary(caller)}\n\n{text}"


# ------------------------------------------------------------
# Menu nodes
# ------------------------------------------------------------

def menunode_main(caller, raw_string="", **kwargs):
    text = "Choose an option:"
    options = [
        {"desc": "Edit name", "goto": "menunode_name"},
        {"desc": "Edit typeclass", "goto": "menunode_type"},
        {"desc": "Edit wear slot", "goto": "menunode_wear"},
        {"desc": "Edit flags", "goto": "menunode_flags"},
        {"desc": "Edit affects", "goto": "menunode_affects"},
        {"desc": "Show prototype", "goto": "menunode_show"},
        {"desc": "List prototypes", "goto": "menunode_list"},
        {"desc": "Save & quit", "goto": "menunode_done"},
        {"desc": "Cancel", "goto": "menunode_cancel"},
    ]
    return _with_summary(caller, text), options


def menunode_show(caller, raw_string="", **kwargs):
    caller.msg(_summary(caller))
    return "menunode_main"


def menunode_list(caller, raw_string="", **kwargs):
    protos = load_all_prototypes("object")
    lines = [f"{v}: {p.get('key', '')}" for v, p in sorted(protos.items())]
    caller.msg("\n".join(lines) or "No prototypes.")
    return "menunode_main"


# ------------------------------------------------------------
# Field editing
# ------------------------------------------------------------

def menunode_name(caller, raw_string="", **kwargs):
    default = caller.ndb.obj_proto.get("key", "")
    text = f"|wObject name|n [current: {default}]"
    options = {"key": "_default", "goto": _set_name}
    return _with_summary(caller, text), options


def _set_name(caller, raw_string, **kwargs):
    val = raw_string.strip()
    if val:
        caller.ndb.obj_proto["key"] = val
    return "menunode_main"


def menunode_type(caller, raw_string="", **kwargs):
    default = caller.ndb.obj_proto.get("typeclass", "")
    text = f"|wTypeclass|n [current: {default}]"
    options = {"key": "_default", "goto": _set_type}
    return _with_summary(caller, text), options


def _set_type(caller, raw_string, **kwargs):
    val = raw_string.strip()
    if val:
        caller.ndb.obj_proto["typeclass"] = val
    return "menunode_main"


def menunode_wear(caller, raw_string="", **kwargs):
    default = caller.ndb.obj_proto.get("slot", "")
    valid = " ".join(sorted(VALID_SLOTS))
    text = f"|wWear slot|n [current: {default}]\nValid: {valid}"
    options = {"key": "_default", "goto": _set_wear}
    return _with_summary(caller, text), options


def _set_wear(caller, raw_string, **kwargs):
    slot = normalize_slot(raw_string.strip())
    if slot and slot in VALID_SLOTS:
        caller.ndb.obj_proto["slot"] = slot
    else:
        caller.msg("Invalid slot name.")
        return "menunode_wear"
    return "menunode_main"


def menunode_flags(caller, raw_string="", **kwargs):
    current = " ".join(caller.ndb.obj_proto.get("flags", []))
    text = f"|wFlags|n (space separated) [current: {current}]"
    options = {"key": "_default", "goto": _set_flags}
    return _with_summary(caller, text), options


def _set_flags(caller, raw_string, **kwargs):
    flags = [f.strip() for f in raw_string.split() if f.strip()]
    caller.ndb.obj_proto["flags"] = flags
    return "menunode_main"


def menunode_affects(caller, raw_string="", **kwargs):
    current = caller.ndb.obj_proto.get("stat_mods", {})
    cur = ", ".join(f"{k}+{v}" for k, v in current.items())
    text = f"|wAffects|n (comma separated STAT+VAL) [current: {cur}]"
    options = {"key": "_default", "goto": _set_affects}
    return _with_summary(caller, text), options


def _set_affects(caller, raw_string, **kwargs):
    try:
        mods, _ = parse_stat_mods(raw_string)
    except ValueError as err:
        caller.msg(f"Invalid modifier: {err}")
        return "menunode_affects"
    caller.ndb.obj_proto["stat_mods"] = mods
    return "menunode_main"


# ------------------------------------------------------------
# Finalization
# ------------------------------------------------------------

def menunode_done(caller, raw_string="", **kwargs):
    vnum = caller.ndb.obj_vnum
    proto = caller.ndb.obj_proto
    save_prototype("object", proto, vnum=vnum)
    caller.msg(f"Object prototype {vnum} saved.")
    caller.ndb.obj_proto = None
    caller.ndb.obj_vnum = None
    return None


def menunode_cancel(caller, raw_string="", **kwargs):
    caller.msg("Editing cancelled.")
    caller.ndb.obj_proto = None
    caller.ndb.obj_vnum = None
    return None


# ------------------------------------------------------------
# Command class
# ------------------------------------------------------------

class CmdOEdit(Command):
    """Open the object prototype editor."""

    key = "oedit"
    locks = "cmd:perm(Builder)"
    help_category = "Building"

    def func(self):
        if not self.args or not self.args.strip().isdigit():
            self.msg("Usage: oedit <vnum>")
            return
        vnum = int(self.args.strip())
        proto = load_prototype("object", vnum)
        if proto is None:
            if not validate_vnum(vnum, "object"):
                self.msg("Invalid or already used VNUM.")
                return
            register_vnum(vnum)
            proto = {"key": f"object_{vnum}", "typeclass": "typeclasses.objects.Object"}
        self.caller.ndb.obj_proto = dict(proto)
        self.caller.ndb.obj_vnum = vnum
        state = OLCState(data=self.caller.ndb.obj_proto, vnum=vnum, original=dict(self.caller.ndb.obj_proto))
        OLCEditor(
            self.caller,
            "commands.oedit",
            startnode="menunode_main",
            state=state,
            validator=OLCValidator(),
        ).start()

