# EvMenu-driven room editor

from __future__ import annotations

from olc.base import OLCEditor, OLCState, OLCValidator
from utils.prototype_manager import save_prototype
from utils.vnum_registry import validate_vnum, register_vnum
from world.areas import find_area_by_vnum
from .building import DIR_FULL, OPPOSITE
from .command import Command


VALID_ROOM_FLAGS = (
    "dark",
    "nopvp",
    "sanctuary",
    "indoors",
    "safe",
    "no_recall",
    "no_mount",
    "no_flee",
    "rest_area",
)


def _summary(caller) -> str:
    data = caller.ndb.room_protos.get(caller.ndb.current_vnum)
    if not data:
        return ""
    lines = [f"|wEditing room {data['vnum']}|n"]
    lines.append(f"Name: {data.get('key', '')}")
    desc = data.get('desc', '')
    if desc:
        lines.append(f"Desc: {desc}")
    flags = ", ".join(data.get('flags', []))
    if flags:
        lines.append(f"Flags: {flags}")
    exits = data.get('exits', {})
    if exits:
        exit_lines = [f"  {dir} -> {v}" for dir, v in exits.items()]
        lines.append("Exits:\n" + "\n".join(exit_lines))
    return "\n".join(lines)


def menunode_main(caller, raw_string="", **kwargs):
    text = _summary(caller)
    options = [
        {"desc": "Edit name", "goto": "menunode_name"},
        {"desc": "Edit description", "goto": "menunode_desc"},
        {"desc": "Edit flags", "goto": "menunode_flags"},
        {"desc": "Edit exits", "goto": "menunode_exits"},
        {"desc": "Show prototype", "goto": "menunode_show"},
        {"desc": "List prototypes", "goto": "menunode_rlist"},
        {"desc": "Save & quit", "goto": "menunode_done"},
        {"desc": "Cancel", "goto": "menunode_cancel"},
    ]
    return text, options


def menunode_show(caller, raw_string="", **kwargs):
    caller.msg(_summary(caller))
    return "menunode_main"


def menunode_rlist(caller, raw_string="", **kwargs):
    lines = [f"{v}: {data.get('key', '')}" for v, data in caller.ndb.room_protos.items()]
    caller.msg("\n".join(lines) or "No prototypes.")
    return "menunode_main"


def menunode_name(caller, raw_string="", **kwargs):
    default = caller.ndb.room_protos[caller.ndb.current_vnum].get("key", "")
    text = f"|wRoom name|n [current: {default}]"
    options = {"key": "_default", "goto": _set_name}
    return text, options


def _set_name(caller, raw_string, **kwargs):
    if not raw_string.strip():
        caller.msg("Name unchanged.")
    else:
        caller.ndb.room_protos[caller.ndb.current_vnum]["key"] = raw_string.strip()
    return "menunode_main"


def menunode_desc(caller, raw_string="", **kwargs):
    default = caller.ndb.room_protos[caller.ndb.current_vnum].get("desc", "")
    text = f"|wRoom description|n [current: {default}]"
    options = {"key": "_default", "goto": _set_desc}
    return text, options


def _set_desc(caller, raw_string, **kwargs):
    caller.ndb.room_protos[caller.ndb.current_vnum]["desc"] = raw_string.strip()
    return "menunode_main"


def menunode_flags(caller, raw_string="", **kwargs):
    current = ", ".join(caller.ndb.room_protos[caller.ndb.current_vnum].get("flags", []))
    text = "|wRoom flags|n (comma separated). Valid: " + ", ".join(VALID_ROOM_FLAGS)
    if current:
        text += f" [current: {current}]"
    options = {"key": "_default", "goto": _set_flags}
    return text, options


def _set_flags(caller, raw_string, **kwargs):
    flags = [f.strip().lower() for f in raw_string.split(',') if f.strip()]
    invalid = [f for f in flags if f not in VALID_ROOM_FLAGS]
    if invalid:
        caller.msg("Invalid flags: " + ", ".join(invalid))
        return "menunode_flags"
    caller.ndb.room_protos[caller.ndb.current_vnum]["flags"] = flags
    return "menunode_main"


def menunode_exits(caller, raw_string="", **kwargs):
    exits = caller.ndb.room_protos[caller.ndb.current_vnum].get("exits", {})
    lines = ["Current exits:"]
    for d, v in exits.items():
        lines.append(f"  {d} -> {v}")
    lines.append("Enter 'set <dir> <vnum>' to add/edit, 'del <dir>' to remove, 'dig <dir> <vnum>' to make new room.")
    text = "\n".join(lines)
    options = {"key": "_default", "goto": _handle_exit_cmd}
    return text, options


def _handle_exit_cmd(caller, raw_string, **kwargs):
    args = raw_string.strip().split()
    if not args:
        return "menunode_main"
    cmd = args[0].lower()
    if cmd == "del" and len(args) == 2:
        dirkey = DIR_FULL.get(args[1].lower())
        if not dirkey:
            caller.msg("Unknown direction.")
            return "menunode_exits"
        caller.ndb.room_protos[caller.ndb.current_vnum].get("exits", {}).pop(dirkey, None)
        return "menunode_exits"
    if cmd == "set" and len(args) == 3:
        dirkey = DIR_FULL.get(args[1].lower())
        if not dirkey or not args[2].isdigit():
            caller.msg("Usage: set <dir> <vnum>")
            return "menunode_exits"
        caller.ndb.room_protos[caller.ndb.current_vnum].setdefault("exits", {})[dirkey] = int(args[2])
        return "menunode_exits"
    if cmd == "dig" and len(args) == 3:
        dirkey = DIR_FULL.get(args[1].lower())
        if not dirkey or not args[2].isdigit():
            caller.msg("Usage: dig <dir> <vnum>")
            return "menunode_exits"
        vnum = int(args[2])
        if not validate_vnum(vnum, "room"):
            caller.msg("Invalid or used vnum.")
            return "menunode_exits"
        register_vnum(vnum)
        current_vnum = caller.ndb.current_vnum
        caller.ndb.room_protos[current_vnum].setdefault("exits", {})[dirkey] = vnum
        new_proto = {"vnum": vnum, "key": f"Room {vnum}", "desc": "", "flags": [], "exits": {OPPOSITE[dirkey]: current_vnum}}
        caller.ndb.room_protos[vnum] = new_proto
        caller.ndb.current_vnum = vnum
        return "menunode_main"
    caller.msg("Unknown command.")
    return "menunode_exits"


def menunode_done(caller, raw_string="", **kwargs):
    for vnum, proto in caller.ndb.room_protos.items():
        data = {
            "typeclass": "typeclasses.rooms.Room",
            "key": proto.get("key") or f"Room {vnum}",
            "desc": proto.get("desc", ""),
        }
        if proto.get("flags"):
            data["tags"] = [(f, "room_flag") for f in proto["flags"]]
        if proto.get("exits"):
            data["exits"] = proto["exits"]
        save_prototype("room", data, vnum=vnum)
    caller.msg("Room prototype(s) saved.")
    caller.ndb.room_protos = None
    caller.ndb.current_vnum = None
    return None


def menunode_cancel(caller, raw_string="", **kwargs):
    caller.ndb.room_protos = None
    caller.ndb.current_vnum = None
    caller.msg("Editing cancelled.")
    return None


class CmdREdit(Command):
    """Room prototype editor."""

    key = "redit"
    locks = "cmd:perm(Builder)"
    help_category = "Building"

    def func(self):
        if not self.args:
            self.msg("Usage: redit create <vnum>")
            return
        parts = self.args.split()
        if len(parts) != 2 or parts[0].lower() != "create":
            self.msg("Usage: redit create <vnum>")
            return
        if not parts[1].isdigit():
            self.msg("VNUM must be numeric.")
            return
        vnum = int(parts[1])
        if not validate_vnum(vnum, "room"):
            self.msg("Invalid or already used VNUM.")
            return
        register_vnum(vnum)
        proto = {"vnum": vnum, "key": f"Room {vnum}", "desc": "", "flags": [], "exits": {}}
        if area := find_area_by_vnum(vnum):
            proto["area"] = area.key
        self.caller.ndb.room_protos = {vnum: proto}
        self.caller.ndb.current_vnum = vnum
        state = OLCState(data=self.caller.ndb.room_protos, vnum=vnum, original=dict(self.caller.ndb.room_protos))
        OLCEditor(
            self.caller,
            "commands.redit",
            startnode="menunode_main",
            state=state,
            validator=OLCValidator(),
        ).start()

