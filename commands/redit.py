# EvMenu-driven room editor

from __future__ import annotations

from olc.base import OLCEditor, OLCState, OLCValidator
import json
from utils.prototype_manager import (
    save_prototype,
    load_prototype,
    load_all_prototypes,
    CATEGORY_DIRS,
)
from utils.vnum_registry import (
    validate_vnum,
    register_vnum,
    unregister_vnum,
    VNUM_RANGES,
)
from world.areas import find_area_by_vnum, get_areas, update_area
from evennia.prototypes import spawner
from world.areas import find_area
from evennia.objects.models import ObjectDB
from typeclasses.rooms import Room
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


def proto_from_room(room) -> dict:
    """Return a prototype dict generated from ``room``."""

    proto = {
        "typeclass": room.typeclass_path,
        "key": room.key,
        "desc": room.db.desc or "",
        "exits": {},
        "vnum": room.db.room_id,
    }

    if area := room.db.area:
        proto["area"] = area

    exits = room.db.exits or {}
    for dirkey, target in exits.items():
        dest_id = getattr(target.db, "room_id", None)
        if isinstance(dest_id, int):
            proto["exits"][dirkey] = dest_id

    flags = room.tags.get(category="room_flag", return_list=True) or []
    if flags:
        proto["flags"] = list(flags)

    try:
        existing = load_prototype("room", room.db.room_id) or {}
    except json.JSONDecodeError:
        existing = {}

    for key in ("spawns", "xyz"):
        if key in existing:
            proto[key] = existing[key]

    return proto


def _state_exists(caller) -> bool:
    """Return ``True`` if the caller has a valid editing state."""
    if not getattr(caller.ndb, "room_protos", None):
        return False
    if getattr(caller.ndb, "current_vnum", None) not in caller.ndb.room_protos:
        return False
    return True


def _summary(caller) -> str:
    if not _state_exists(caller):
        return ""
    data = caller.ndb.room_protos.get(caller.ndb.current_vnum)
    if not data:
        return ""
    lines = [f"|wEditing room {data.get('vnum', caller.ndb.current_vnum)}|n"]
    lines.append(f"Name: {data.get('key', '')}")
    area = data.get("area")
    if area:
        lines.append(f"Area: {area}")
    desc = data.get("desc", "")
    if desc:
        lines.append(f"Desc: {desc}")
    flags = ", ".join(data.get("flags", []))
    if flags:
        lines.append(f"Flags: {flags}")
    exits = data.get("exits", {})
    if exits:
        exit_lines = [f"  {dir} -> {v}" for dir, v in exits.items()]
        lines.append("Exits:\n" + "\n".join(exit_lines))
    spawns = data.get("spawns", [])
    if spawns:
        spawn_lines = []
        for entry in spawns:
            proto = entry.get("prototype") or entry.get("proto")
            maxc = entry.get("max_spawns", entry.get("max_count", 0))
            rate = entry.get("spawn_interval", entry.get("respawn_rate", 0))
            spawn_lines.append(f"  {proto}: max {maxc} every {rate}s")
        lines.append("Spawns:\n" + "\n".join(spawn_lines))
    return "\n".join(lines)


def menunode_main(caller, raw_string="", **kwargs):
    if not _state_exists(caller):
        caller.msg("Room editing state missing. Exiting.")
        return None
    text = _summary(caller)
    options = [
        {"desc": "Edit name", "goto": "menunode_name"},
        {"desc": "Edit description", "goto": "menunode_desc"},
        {"desc": "Edit flags", "goto": "menunode_flags"},
        {"desc": "Edit exits", "goto": "menunode_exits"},
        {"desc": "Edit spawns", "goto": "menunode_spawns"},
        {
            "desc": "View saved prototype for this room",
            "goto": "menunode_view_prototype",
        },
        {"desc": "Browse area prototypes", "goto": "menunode_list_prototypes"},
        {"desc": "Save & quit", "goto": "menunode_done"},
        {"desc": "Cancel", "goto": "menunode_cancel"},
    ]
    return text, options


def menunode_view_prototype(caller, raw_string="", **kwargs):
    """Display the saved prototype for a room."""

    if not _state_exists(caller):
        caller.msg("Room editing state missing. Exiting.")
        return None

    vnum = kwargs.get("vnum", caller.ndb.current_vnum)
    try:
        proto = load_prototype("room", vnum)
    except json.JSONDecodeError:
        caller.msg(f"Error loading prototype for room {vnum}.")
        return "menunode_main"

    if not proto:
        caller.msg("This room does not have a saved prototype.")
        return "menunode_main"

    lines = [f"|wPrototype {vnum}|n"]
    if key := proto.get("key"):
        lines.append(f"Name: {key}")
    if area := proto.get("area"):
        lines.append(f"Area: {area}")
    if desc := proto.get("desc"):
        lines.append(f"Desc: {desc}")
    if flags := proto.get("flags"):
        lines.append("Flags: " + ", ".join(flags))
    exits = proto.get("exits") or {}
    if exits:
        exit_lines = [f"  {d} -> {dest}" for d, dest in exits.items()]
        lines.append("Exits:\n" + "\n".join(exit_lines))

    caller.msg("\n".join(lines))
    return kwargs.get("return_node", "menunode_main")


# alias for backward compatibility
menunode_show = menunode_view_prototype


def menunode_list_prototypes(caller, raw_string="", **kwargs):
    """Browse all prototypes in the current room's area."""

    if not _state_exists(caller):
        caller.msg("Room editing state missing. Exiting.")
        return None

    current = caller.ndb.room_protos.get(caller.ndb.current_vnum, {})
    area_name = current.get("area")
    if not area_name:
        caller.msg("No prototypes found for this room or area.")
        return "menunode_main"

    protos = {
        vnum: proto
        for vnum, proto in load_all_prototypes("room").items()
        if proto.get("area") == area_name
    }

    if raw_string:
        choice = raw_string.strip().lower()
        if choice in {"b", "back"}:
            return "menunode_main"
        if choice.isdigit() and int(choice) in protos:
            return menunode_view_prototype(
                caller,
                vnum=int(choice),
                return_node="menunode_list_prototypes",
            )
        caller.msg("Invalid selection.")
        return "menunode_list_prototypes"

    if not protos:
        caller.msg("No prototypes found for this room or area.")
        return "menunode_main"

    lines = [f"Prototypes in {area_name}:"]
    for vnum, proto in sorted(protos.items()):
        summary = proto.get("desc", "").splitlines()[0] or proto.get("key", "")
        if len(summary) > 40:
            summary = summary[:37] + "..."
        lines.append(f"{vnum}: {proto.get('key', '')} - \"{summary}\"")
    lines.append("Enter VNUM to preview or 'back' to return.")
    text = "\n".join(lines)

    options = {"key": "_default", "goto": menunode_list_prototypes}
    return text, options


# alias for backward compatibility
menunode_rlist = menunode_list_prototypes


def menunode_name(caller, raw_string="", **kwargs):
    if not _state_exists(caller):
        caller.msg("Room editing state missing. Exiting.")
        return None
    default = caller.ndb.room_protos[caller.ndb.current_vnum].get("key", "")
    text = f"|wRoom name|n [current: {default}]"
    options = {"key": "_default", "goto": _set_name}
    return text, options


def _set_name(caller, raw_string, **kwargs):
    if not _state_exists(caller):
        caller.msg("Room editing state missing. Exiting.")
        return None
    if not raw_string.strip():
        caller.msg("Name unchanged.")
    else:
        caller.ndb.room_protos[caller.ndb.current_vnum]["key"] = raw_string.strip()
    return "menunode_main"


def menunode_desc(caller, raw_string="", **kwargs):
    if not _state_exists(caller):
        caller.msg("Room editing state missing. Exiting.")
        return None
    default = caller.ndb.room_protos[caller.ndb.current_vnum].get("desc", "")
    text = f"|wRoom description|n [current: {default}]"
    options = {"key": "_default", "goto": _set_desc}
    return text, options


def _set_desc(caller, raw_string, **kwargs):
    if not _state_exists(caller):
        caller.msg("Room editing state missing. Exiting.")
        return None
    caller.ndb.room_protos[caller.ndb.current_vnum]["desc"] = raw_string.strip()
    return "menunode_main"


def menunode_flags(caller, raw_string="", **kwargs):
    if not _state_exists(caller):
        caller.msg("Room editing state missing. Exiting.")
        return None
    current = ", ".join(
        caller.ndb.room_protos[caller.ndb.current_vnum].get("flags", [])
    )
    text = "|wRoom flags|n (comma separated). Valid: " + ", ".join(VALID_ROOM_FLAGS)
    if current:
        text += f" [current: {current}]"
    options = {"key": "_default", "goto": _set_flags}
    return text, options


def _set_flags(caller, raw_string, **kwargs):
    if not _state_exists(caller):
        caller.msg("Room editing state missing. Exiting.")
        return None
    flags = [f.strip().lower() for f in raw_string.split(",") if f.strip()]
    invalid = [f for f in flags if f not in VALID_ROOM_FLAGS]
    if invalid:
        caller.msg("Invalid flags: " + ", ".join(invalid))
        return "menunode_flags"
    caller.ndb.room_protos[caller.ndb.current_vnum]["flags"] = flags
    return "menunode_main"


def menunode_exits(caller, raw_string="", **kwargs):
    if not _state_exists(caller):
        caller.msg("Room editing state missing. Exiting.")
        return None
    exits = caller.ndb.room_protos[caller.ndb.current_vnum].get("exits", {})
    lines = ["Current exits:"]
    for d, v in exits.items():
        lines.append(f"  {d} -> {v}")
    lines.append(
        "Enter 'set <dir> <vnum>' to add/edit, 'del <dir>' to remove, 'dig <dir> <vnum>' to make new room."
    )
    text = "\n".join(lines)
    options = {"key": "_default", "goto": _handle_exit_cmd}
    return text, options


def _handle_exit_cmd(caller, raw_string, **kwargs):
    if not _state_exists(caller):
        caller.msg("Room editing state missing. Exiting.")
        return None
    args = raw_string.strip().split()
    if not args:
        return "menunode_main"
    cmd = args[0].lower()
    if cmd == "del" and len(args) == 2:
        dirkey = DIR_FULL.get(args[1].lower())
        if not dirkey:
            caller.msg("Unknown direction.")
            return "menunode_exits"
        caller.ndb.room_protos[caller.ndb.current_vnum].get("exits", {}).pop(
            dirkey, None
        )
        return "menunode_exits"
    if cmd == "set" and len(args) == 3:
        dirkey = DIR_FULL.get(args[1].lower())
        if not dirkey or not args[2].isdigit():
            caller.msg("Usage: set <dir> <vnum>")
            return "menunode_exits"
        caller.ndb.room_protos[caller.ndb.current_vnum].setdefault("exits", {})[
            dirkey
        ] = int(args[2])
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
        new_proto = {
            "vnum": vnum,
            "key": f"Room {vnum}",
            "desc": "",
            "flags": [],
            "exits": {OPPOSITE[dirkey]: current_vnum},
        }
        caller.ndb.room_protos[vnum] = new_proto
        caller.ndb.current_vnum = vnum
        return "menunode_main"
    caller.msg("Unknown command.")
    return "menunode_exits"


def menunode_spawns(caller, raw_string="", **kwargs):
    """Menu node for editing NPC spawn data."""

    if not _state_exists(caller):
        caller.msg("Room editing state missing. Exiting.")
        return None
    proto = caller.ndb.room_protos[caller.ndb.current_vnum]
    spawns = proto.get("spawns", [])
    lines = ["Current spawns:"]
    if spawns:
        for entry in spawns:
            proto_key = entry.get("prototype") or entry.get("proto")
            maxc = entry.get("max_spawns", entry.get("max_count", 0))
            rate = entry.get("spawn_interval", entry.get("respawn_rate", 0))
            lines.append(f"  {proto_key}: max {maxc} every {rate}s")
    else:
        lines.append("  None")
    lines.append("Commands:\n  add <proto> <max> <rate>\n  remove <proto>\n  done")
    text = "\n".join(lines)
    options = {"key": "_default", "goto": _handle_spawn_cmd}
    return text, options


def _handle_spawn_cmd(caller, raw_string, **kwargs):
    if not _state_exists(caller):
        caller.msg("Room editing state missing. Exiting.")
        return None
    string = raw_string.strip()
    proto = caller.ndb.room_protos[caller.ndb.current_vnum]
    spawns = proto.setdefault("spawns", [])
    if not string or string.lower() in {"done", "back"}:
        return "menunode_main"
    if string.lower().startswith("add "):
        parts = string.split()
        if len(parts) != 4:
            caller.msg("Usage: add <proto> <max> <rate>")
            return "menunode_spawns"
        proto_key = parts[1]
        if proto_key.isdigit():
            proto_key = int(proto_key)
        try:
            maxc = int(parts[2])
            rate = int(parts[3])
        except ValueError:
            caller.msg("Counts and rate must be numbers.")
            return "menunode_spawns"
        for entry in spawns:
            if (entry.get("prototype") or entry.get("proto")) == proto_key:
                entry.update(
                    {
                        "max_spawns": maxc,
                        "spawn_interval": rate,
                    }
                )
                break
        else:
            spawns.append(
                {
                    "prototype": proto_key,
                    "max_spawns": maxc,
                    "spawn_interval": rate,
                    "location": caller.ndb.current_vnum,
                }
            )
        return "menunode_spawns"
    if string.lower().startswith("remove "):
        proto_key = string.split(None, 1)[1].strip()
        if proto_key.isdigit():
            proto_key = int(proto_key)
        for entry in list(spawns):
            if (entry.get("prototype") or entry.get("proto")) == proto_key:
                spawns.remove(entry)
                break
        return "menunode_spawns"
    caller.msg("Unknown command.")
    return "menunode_spawns"


def menunode_done(caller, raw_string="", **kwargs):
    if not _state_exists(caller):
        caller.msg("Room editing state missing. Exiting.")
        return None
    for vnum, proto in caller.ndb.room_protos.items():
        try:
            existing = load_prototype("room", vnum) or {}
        except json.JSONDecodeError:
            existing = {}

        # reload current room exits so changes outside the editor are kept
        objs = ObjectDB.objects.filter(
            db_attributes__db_key="room_id",
            db_attributes__db_value=vnum,
        )
        room_obj = next((o for o in objs if o.is_typeclass(Room, exact=False)), None)

        current_exits = {}
        if room_obj:
            for dirkey, target in (room_obj.db.exits or {}).items():
                dest_id = getattr(target.db, "room_id", None)
                if isinstance(dest_id, int):
                    current_exits[dirkey] = dest_id

        existing_exits = existing.get("exits", {})
        base_exits = {**existing_exits, **current_exits}

        proto_exits = proto.get("exits")
        if proto_exits is not None:
            if proto_exits == existing_exits:
                final_exits = base_exits
            else:
                final_exits = base_exits.copy()
                for dirkey in set(existing_exits) - set(proto_exits):
                    final_exits.pop(dirkey, None)
                final_exits.update(proto_exits)
        else:
            final_exits = base_exits
        proto["exits"] = final_exits

        data = dict(existing)
        data.update(
            {
                "typeclass": "typeclasses.rooms.Room",
                "key": proto.get("key") or existing.get("key") or f"Room {vnum}",
                "desc": proto.get("desc", existing.get("desc", "")),
            }
        )

        area_key = proto.get("area") or existing.get("area")
        if area_key and "area" not in proto:
            proto["area"] = area_key
        if not area_key and room_obj:
            area_key = room_obj.attributes.get("area")
            if area_key:
                proto["area"] = area_key
        if not area_key:
            caller.msg("Error: This room has no area assigned. Cannot save prototype.")
            return menunode_main(caller)
        if "flags" in proto:
            data["tags"] = [(f, "room_flag") for f in proto.get("flags", [])]
        if "exits" in proto:
            data["exits"] = proto.get("exits") or {}
        if "spawns" in proto:
            data["spawns"] = proto.get("spawns") or []
        save_prototype("room", data, vnum=vnum)

        idx, area = find_area(area_key)
        if area and vnum not in area.rooms:
            area.rooms.append(vnum)
            update_area(idx, area)

        # update live room object if it exists
        room = room_obj
        if room:
            room.key = data["key"]
            room.db.desc = data["desc"]
            if proto.get("area") is not None:
                room.db.area = proto["area"]

            flags = None
            if "flags" in proto:
                flags = proto.get("flags", [])
            elif isinstance(existing.get("tags"), list):
                flags = [
                    t[0] if isinstance(t, (list, tuple)) else t
                    for t in existing["tags"]
                ]

            if flags is not None:
                room.tags.clear(category="room_flag")
                for flag in flags:
                    room.tags.add(flag, category="room_flag")

            exits_data = None
            if "exits" in proto:
                exits_data = proto.get("exits") or {}
            elif existing.get("exits"):
                exits_data = existing["exits"]

            if exits_data is not None:
                exits = {}
                for dirkey, dest in exits_data.items():
                    dest_obj = ObjectDB.objects.filter(
                        db_attributes__db_key="room_id",
                        db_attributes__db_value=dest,
                    ).first()
                    if dest_obj and dest_obj.is_typeclass(Room, exact=False):
                        exits[dirkey] = dest_obj
                room.db.exits = exits

        from evennia.scripts.models import ScriptDB

        script = ScriptDB.objects.filter(db_key="spawn_manager").first()
        if script and hasattr(script, "register_room_spawn"):
            script.register_room_spawn(proto)
            if hasattr(script, "force_respawn"):
                script.force_respawn(vnum)
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
        def _clear_state():
            self.caller.ndb.room_protos = None
            self.caller.ndb.current_vnum = None

        if not self.args:
            self.msg(
                "Usage: redit <vnum> | redit create <vnum> | redit here <vnum> | redit live <vnum> | redit vnum <old> <new>"
            )
            _clear_state()
            return

        parts = self.args.split()
        sub = parts[0].lower()

        if len(parts) == 1 and parts[0].isdigit():
            vnum = int(parts[0])
            try:
                proto = load_prototype("room", vnum)
            except json.JSONDecodeError:
                self.msg(
                    f"Error loading prototype for room {vnum}. Try 'redit create {vnum}'."
                )
                _clear_state()
                return
            if proto is None:
                objs = ObjectDB.objects.filter(
                    db_attributes__db_key="room_id",
                    db_attributes__db_value=vnum,
                )
                room = next(
                    (o for o in objs if o.is_typeclass(Room, exact=False)), None
                )
                if room:
                    proto = proto_from_room(room)
                    self.msg(f"Editing live room #{vnum} (no prototype found).")
                else:
                    self.msg(
                        f"Room VNUM {vnum} not found. Use `redit create {vnum}` to make a new room."
                    )
                    _clear_state()
                    return
            else:
                if "area" not in proto:
                    objs = ObjectDB.objects.filter(
                        db_attributes__db_key="room_id",
                        db_attributes__db_value=vnum,
                    )
                    room_obj = next(
                        (o for o in objs if o.is_typeclass(Room, exact=False)),
                        None,
                    )
                    if room_obj and room_obj.db.area:
                        proto["area"] = room_obj.db.area
            self.caller.ndb.room_protos = {vnum: proto}
            self.caller.ndb.current_vnum = vnum
            state = OLCState(
                data=self.caller.ndb.room_protos,
                vnum=vnum,
                original=dict(self.caller.ndb.room_protos),
            )
            OLCEditor(
                self.caller,
                "commands.redit",
                startnode="menunode_main",
                state=state,
                validator=OLCValidator(),
            ).start()
            return

        if sub == "vnum" and len(parts) == 3:
            old_str, new_str = parts[1], parts[2]
            if not (old_str.isdigit() and new_str.isdigit()):
                self.msg(
                    "Usage: redit <vnum> | redit create <vnum> | redit here <vnum> | redit live <vnum> | redit vnum <old> <new>"
                )
                _clear_state()
                return
            old_vnum, new_vnum = int(old_str), int(new_str)
            proto = load_prototype("room", old_vnum)
            if proto is None:
                self.msg("Prototype not found.")
                _clear_state()
                return
            if not validate_vnum(new_vnum, "room"):
                self.msg("Invalid or already used VNUM.")
                _clear_state()
                return
            save_prototype("room", proto, vnum=new_vnum)
            old_path = CATEGORY_DIRS["room"] / f"{old_vnum}.json"
            if old_path.exists():
                old_path.unlink()
            unregister_vnum(old_vnum, "room")
            register_vnum(new_vnum)

            # update exits in other room prototypes
            protos = load_all_prototypes("room")
            for vnum, p in protos.items():
                exits = p.get("exits", {})
                changed = False
                for dirkey, dest in list(exits.items()):
                    if dest == old_vnum:
                        exits[dirkey] = new_vnum
                        changed = True
                if changed:
                    save_prototype("room", p, vnum=vnum)

            # update area room lists
            areas = get_areas()
            for idx, area in enumerate(areas):
                if old_vnum in area.rooms:
                    area.rooms = [new_vnum if r == old_vnum else r for r in area.rooms]
                    update_area(idx, area)

            self.msg(f"Room prototype {old_vnum} moved to {new_vnum}.")
            return

        if sub == "here" and len(parts) == 2 and parts[1].isdigit():
            vnum = int(parts[1])
            room = self.caller.location
            if not room:
                self.msg("You have no location.")
                _clear_state()
                return
            if not validate_vnum(vnum, "room"):
                start, end = VNUM_RANGES["room"]
                self.msg(
                    f"Invalid or already used VNUM. Rooms use {start}-{end}. "
                    "Try @nextvnum R."
                )
                _clear_state()
                return
            area_name = room.db.area
            area = None
            idx = -1
            if area_name:
                idx, area = find_area(area_name)
                if area and not (area.start <= vnum <= area.end):
                    self.msg("Number outside area range.")
                    _clear_state()
                    return
                objs = ObjectDB.objects.filter(
                    db_attributes__db_key="area",
                    db_attributes__db_strvalue__iexact=area_name,
                )
                for obj in objs:
                    if obj == room:
                        continue
                    if obj.db.room_id == vnum and obj.is_typeclass(Room, exact=False):
                        self.msg("Room already exists.")
                        _clear_state()
                        return

            register_vnum(vnum)
            proto = {
                "typeclass": "typeclasses.rooms.Room",
                "key": room.key,
                "desc": room.db.desc or "",
                "exits": {},
            }
            if area_name:
                proto["area"] = area_name
            exits = room.db.exits or {}
            for dirkey, target in exits.items():
                dest_id = getattr(target.db, "room_id", None)
                if isinstance(dest_id, int):
                    proto["exits"][dirkey] = dest_id
            flags = room.tags.get(category="room_flag", return_list=True) or []
            if flags:
                proto["flags"] = list(flags)
            save_prototype("room", proto, vnum=vnum)

            room.set_area(area_name, vnum)
            if area and vnum not in area.rooms:
                area.rooms.append(vnum)
                update_area(idx, area)

            self.caller.ndb.room_protos = {vnum: proto}
            self.caller.ndb.current_vnum = vnum
            state = OLCState(
                data=self.caller.ndb.room_protos,
                vnum=vnum,
                original=dict(self.caller.ndb.room_protos),
            )
            OLCEditor(
                self.caller,
                "commands.redit",
                startnode="menunode_main",
                state=state,
                validator=OLCValidator(),
            ).start()
            return

        if sub == "live" and len(parts) == 2 and parts[1].isdigit():
            vnum = int(parts[1])
            objs = ObjectDB.objects.filter(
                db_attributes__db_key="room_id",
                db_attributes__db_value=vnum,
            )
            room = next((o for o in objs if o.is_typeclass(Room, exact=False)), None)
            if not room:
                self.msg(f"Room VNUM {vnum} not found.")
                _clear_state()
                return
            proto = proto_from_room(room)
            self.caller.ndb.room_protos = {vnum: proto}
            self.caller.ndb.current_vnum = vnum
            state = OLCState(
                data=self.caller.ndb.room_protos,
                vnum=vnum,
                original=dict(self.caller.ndb.room_protos),
            )
            OLCEditor(
                self.caller,
                "commands.redit",
                startnode="menunode_main",
                state=state,
                validator=OLCValidator(),
            ).start()
            return

        if sub != "create" or len(parts) != 2:
            self.msg(
                "Usage: redit <vnum> | redit create <vnum> | redit here <vnum> | redit live <vnum> | redit vnum <old> <new>"
            )
            _clear_state()
            return

        if not parts[1].isdigit():
            self.msg("VNUM must be numeric.")
            _clear_state()
            return
        vnum = int(parts[1])
        if not validate_vnum(vnum, "room"):
            start, end = VNUM_RANGES["room"]
            self.msg(
                f"Invalid or already used VNUM. Rooms use {start}-{end}. "
                "Try @nextvnum R."
            )
            _clear_state()
            return
        register_vnum(vnum)
        proto = load_prototype("room", vnum)
        if proto is None:
            proto = {
                "typeclass": "typeclasses.rooms.Room",
                "key": f"Room {vnum}",
                "desc": "",
                "exits": {},
            }
            if area := find_area_by_vnum(vnum):
                proto["area"] = area.key
            save_prototype("room", proto, vnum=vnum)
        area = None
        idx = -1
        if self.caller.location and self.caller.location.db.area:
            idx, area = find_area(self.caller.location.db.area)
        if area is None:
            area = find_area_by_vnum(vnum)
            if area:
                idx, _ = find_area(area.key)
        room = spawner.spawn(proto)[0]
        room.db.room_id = vnum
        if area:
            room.set_area(area.key, vnum)
            if vnum not in area.rooms:
                area.rooms.append(vnum)
                update_area(idx, area)
            self.msg(f"Room {vnum} created and registered to area '{area.key}'")
        else:
            self.msg(f"Room {vnum} created.")
        self.caller.ndb.room_protos = {vnum: proto}
        self.caller.ndb.current_vnum = vnum
        state = OLCState(
            data=self.caller.ndb.room_protos,
            vnum=vnum,
            original=dict(self.caller.ndb.room_protos),
        )
        OLCEditor(
            self.caller,
            "commands.redit",
            startnode="menunode_main",
            state=state,
            validator=OLCValidator(),
        ).start()
