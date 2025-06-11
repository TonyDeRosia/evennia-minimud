# Menu driven mob prototype editor

from evennia.utils.evmenu import EvMenu
from utils.prototype_manager import (
    load_prototype,
    save_prototype,
    load_all_prototypes,
)
from utils.vnum_registry import validate_vnum, register_vnum
from world.mob_constants import (
    ACTFLAGS,
    AFFECTED_BY,
    SPECIAL_FUNCS,
    parse_flag_list,
)
from .command import Command


# ------------------------------------------------------------
# Helper functions
# ------------------------------------------------------------

def _summary(caller) -> str:
    """Return a short summary of the prototype being edited."""
    proto = caller.ndb.mob_proto or {}
    vnum = caller.ndb.mob_vnum
    lines = [f"|wEditing mob {vnum}|n"]
    lines.append(f"Key: {proto.get('key', '')}")
    desc = proto.get("desc")
    if desc:
        lines.append(f"Desc: {desc}")
    lvl = proto.get("level")
    if lvl is not None:
        lines.append(f"Level: {lvl}")
    hp = proto.get("hp")
    if hp is not None:
        lines.append(f"HP: {hp}")
    mp = proto.get("mp")
    if mp is not None:
        lines.append(f"MP: {mp}")
    sp = proto.get("sp")
    if sp is not None:
        lines.append(f"SP: {sp}")
    flags = []
    flags.extend(proto.get("actflags", []))
    flags.extend(proto.get("affected_by", []))
    if flags:
        lines.append("Flags: " + ", ".join(flags))
    ai = proto.get("ai_type")
    if ai:
        lines.append(f"AI: {ai}")
    special = proto.get("special_funcs")
    if special:
        if isinstance(special, list):
            lines.append("Special: " + ", ".join(special))
        else:
            lines.append(f"Special: {special}")
    if proto.get("mobprogs"):
        lines.append(f"Mobprogs: {len(proto.get('mobprogs'))}")
    return "\n".join(lines)


def _with_summary(caller, text: str) -> str:
    return f"{_summary(caller)}\n\n{text}"


def _set_simple(caller, raw_string, field: str, cast=int):
    if not raw_string.strip():
        caller.msg("No value entered.")
        return f"menunode_{field}"
    try:
        val = cast(raw_string.strip())
    except (TypeError, ValueError):
        caller.msg("Invalid value.")
        return f"menunode_{field}"
    caller.ndb.mob_proto[field] = val
    return "menunode_stats"


def menunode_main(caller, raw_string="", **kwargs):
    text = "Choose an option:"
    options = [
        {"desc": "Edit key", "goto": "menunode_key"},
        {"desc": "Edit description", "goto": "menunode_desc"},
        {"desc": "Edit stats", "goto": "menunode_stats"},
        {"desc": "Edit flags", "goto": "menunode_flags"},
        {"desc": "Edit behaviors", "goto": "menunode_behavior"},
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
    protos = load_all_prototypes("npc")
    lines = [f"{v}: {p.get('key', '')}" for v, p in sorted(protos.items())]
    caller.msg("\n".join(lines) or "No prototypes.")
    return "menunode_main"


# ------------------------------------------------------------
# Basic fields
# ------------------------------------------------------------

def menunode_key(caller, raw_string="", **kwargs):
    default = caller.ndb.mob_proto.get("key", "")
    text = f"|wMob key|n [current: {default}]"
    options = {"key": "_default", "goto": _set_key}
    return _with_summary(caller, text), options


def _set_key(caller, raw_string, **kwargs):
    val = raw_string.strip()
    if val:
        caller.ndb.mob_proto["key"] = val
    return "menunode_main"


def menunode_desc(caller, raw_string="", **kwargs):
    default = caller.ndb.mob_proto.get("desc", "")
    text = f"|wMob description|n [current: {default}]"
    options = {"key": "_default", "goto": _set_desc}
    return _with_summary(caller, text), options


def _set_desc(caller, raw_string, **kwargs):
    caller.ndb.mob_proto["desc"] = raw_string.strip()
    return "menunode_main"


# ------------------------------------------------------------
# Stats editing
# ------------------------------------------------------------

def menunode_stats(caller, raw_string="", **kwargs):
    text = "Select stat to edit:"
    options = [
        {"desc": "Level", "goto": "menunode_level"},
        {"desc": "HP", "goto": ("menunode_hp", {})},
        {"desc": "MP", "goto": ("menunode_mp", {})},
        {"desc": "SP", "goto": ("menunode_sp", {})},
        {"desc": "Damage", "goto": ("menunode_damage", {})},
        {"desc": "Armor", "goto": ("menunode_armor", {})},
        {"desc": "Back", "goto": "menunode_main"},
    ]
    return _with_summary(caller, text), options


def menunode_level(caller, raw_string="", **kwargs):
    default = caller.ndb.mob_proto.get("level", "")
    text = f"|wLevel|n [current: {default}]"
    options = {"key": "_default", "goto": lambda c, s: _set_simple(c, s, "level", int)}
    return _with_summary(caller, text), options


def menunode_hp(caller, raw_string="", **kwargs):
    default = caller.ndb.mob_proto.get("hp", "")
    text = f"|wHP|n [current: {default}]"
    options = {"key": "_default", "goto": lambda c, s: _set_simple(c, s, "hp", int)}
    return _with_summary(caller, text), options


def menunode_mp(caller, raw_string="", **kwargs):
    default = caller.ndb.mob_proto.get("mp", "")
    text = f"|wMP|n [current: {default}]"
    options = {"key": "_default", "goto": lambda c, s: _set_simple(c, s, "mp", int)}
    return _with_summary(caller, text), options


def menunode_sp(caller, raw_string="", **kwargs):
    default = caller.ndb.mob_proto.get("sp", "")
    text = f"|wSP|n [current: {default}]"
    options = {"key": "_default", "goto": lambda c, s: _set_simple(c, s, "sp", int)}
    return _with_summary(caller, text), options


def menunode_damage(caller, raw_string="", **kwargs):
    default = caller.ndb.mob_proto.get("damage", "")
    text = f"|wDamage|n [current: {default}]"
    options = {"key": "_default", "goto": lambda c, s: _set_simple(c, s, "damage", int)}
    return _with_summary(caller, text), options


def menunode_armor(caller, raw_string="", **kwargs):
    default = caller.ndb.mob_proto.get("armor", "")
    text = f"|wArmor|n [current: {default}]"
    options = {"key": "_default", "goto": lambda c, s: _set_simple(c, s, "armor", int)}
    return _with_summary(caller, text), options


# ------------------------------------------------------------
# Flags and behaviors
# ------------------------------------------------------------

def menunode_flags(caller, raw_string="", **kwargs):
    text = "Edit which flags?"
    options = [
        {"desc": "Actflags", "goto": "menunode_actflags"},
        {"desc": "Affected by", "goto": "menunode_affects"},
        {"desc": "Back", "goto": "menunode_main"},
    ]
    return _with_summary(caller, text), options


def menunode_actflags(caller, raw_string="", **kwargs):
    current = " ".join(caller.ndb.mob_proto.get("actflags", []))
    valid = " ".join(f.value for f in ACTFLAGS)
    text = f"|wAct flags|n (space separated). Valid: {valid}\nCurrent: {current}"
    options = {"key": "_default", "goto": _set_actflags}
    return _with_summary(caller, text), options


def _set_actflags(caller, raw_string, **kwargs):
    flags = [f.value for f in parse_flag_list(raw_string, ACTFLAGS)]
    caller.ndb.mob_proto["actflags"] = flags
    return "menunode_flags"


def menunode_affects(caller, raw_string="", **kwargs):
    current = " ".join(caller.ndb.mob_proto.get("affected_by", []))
    valid = " ".join(f.value for f in AFFECTED_BY)
    text = f"|wAffected by|n (space separated). Valid: {valid}\nCurrent: {current}"
    options = {"key": "_default", "goto": _set_affects}
    return _with_summary(caller, text), options


def _set_affects(caller, raw_string, **kwargs):
    flags = [f.value for f in parse_flag_list(raw_string, AFFECTED_BY)]
    caller.ndb.mob_proto["affected_by"] = flags
    return "menunode_flags"


def menunode_behavior(caller, raw_string="", **kwargs):
    text = "Edit behaviors:"
    options = [
        {"desc": "AI type", "goto": "menunode_ai"},
        {"desc": "Special funcs", "goto": "menunode_special"},
        {"desc": "Back", "goto": "menunode_main"},
    ]
    return _with_summary(caller, text), options


def menunode_ai(caller, raw_string="", **kwargs):
    current = caller.ndb.mob_proto.get("ai_type", "")
    text = f"|wAI type|n [current: {current}]"
    options = {"key": "_default", "goto": _set_ai}
    return _with_summary(caller, text), options


def _set_ai(caller, raw_string, **kwargs):
    caller.ndb.mob_proto["ai_type"] = raw_string.strip()
    return "menunode_behavior"


def menunode_special(caller, raw_string="", **kwargs):
    current = " ".join(caller.ndb.mob_proto.get("special_funcs", []))
    valid = " ".join(f.value for f in SPECIAL_FUNCS)
    text = f"|wSpecial funcs|n (space separated). Valid: {valid}\nCurrent: {current}"
    options = {"key": "_default", "goto": _set_special}
    return _with_summary(caller, text), options


def _set_special(caller, raw_string, **kwargs):
    funcs = [f.value for f in parse_flag_list(raw_string, SPECIAL_FUNCS)]
    caller.ndb.mob_proto["special_funcs"] = funcs
    return "menunode_behavior"


# ------------------------------------------------------------
# Finalization nodes
# ------------------------------------------------------------

def menunode_done(caller, raw_string="", **kwargs):
    vnum = caller.ndb.mob_vnum
    proto = caller.ndb.mob_proto
    save_prototype("npc", proto, vnum=vnum)
    caller.msg(f"Mob prototype {vnum} saved.")
    caller.ndb.mob_proto = None
    caller.ndb.mob_vnum = None
    return None


def menunode_cancel(caller, raw_string="", **kwargs):
    caller.msg("Editing cancelled.")
    caller.ndb.mob_proto = None
    caller.ndb.mob_vnum = None
    return None


# ------------------------------------------------------------
# Command class
# ------------------------------------------------------------

class CmdMEdit(Command):
    """Open the mob prototype editor."""

    key = "medit"
    locks = "cmd:perm(Builder)"
    help_category = "Building"

    def func(self):
        if not self.args or not self.args.strip().isdigit():
            self.msg("Usage: medit <vnum>")
            return
        vnum = int(self.args.strip())
        proto = load_prototype("npc", vnum)
        if proto is None:
            if not validate_vnum(vnum, "npc"):
                self.msg("Invalid or already used VNUM.")
                return
            register_vnum(vnum)
            proto = {"key": f"mob_{vnum}", "level": 1}
        self.caller.ndb.mob_proto = dict(proto)
        self.caller.ndb.mob_vnum = vnum
        EvMenu(self.caller, "commands.medit", startnode="menunode_main")

