from evennia.utils.evtable import EvTable
from evennia import CmdSet
from evennia.objects.models import ObjectDB
from evennia.server.models import ServerConfig
from typeclasses.rooms import Room
from .command import Command
from world.areas import (
    Area,
    get_areas,
    save_area,
    update_area,
    find_area,
    parse_area_identifier,
)
from world import area_npcs
from olc.base import OLCValidator
from utils.prototype_manager import (
    load_all_prototypes,
    load_prototype,
    save_prototype,
)


class AreaValidator(OLCValidator):
    """Simple validator for area data."""

    def validate(self, data: dict) -> list[str]:  # type: ignore[override]
        warnings: list[str] = []
        start = data.get("start")
        end = data.get("end")
        if start is not None and end is not None and start > end:
            warnings.append("Start VNUM greater than end; values swapped.")
        return warnings


class CmdAList(Command):
    """List defined areas."""

    key = "alist"
    locks = "cmd:perm(Builder)"
    help_category = "Building"

    def func(self):
        if self.args.strip().lower() == "current":
            room = self.caller.location
            if room and room.db.area:
                self.msg(f"Current area: {room.db.area}")
            else:
                self.msg("This room is not within a registered area.")
            return

        areas = get_areas()
        spawn_entries = ServerConfig.objects.conf("spawn_registry", default=list)
        spawn_counts: dict[str, int] = {}
        for entry in spawn_entries:
            key = str(entry.get("area", "")).lower()
            spawn_counts[key] = spawn_counts.get(key, 0) + 1
        if not areas:
            area_data: dict[str, dict] = {}
            # gather from existing rooms
            objs = ObjectDB.objects.filter(db_attributes__db_key="area")
            for obj in objs:
                if not obj.is_typeclass(Room, exact=False):
                    continue
                name = obj.attributes.get("area")
                if not name:
                    continue
                info = area_data.setdefault(name, {"room_ids": [], "room_count": 0, "mob_count": 0})
                info["room_count"] += 1
                room_id = obj.attributes.get("room_id")
                if room_id is not None:
                    try:
                        info["room_ids"].append(int(room_id))
                    except (TypeError, ValueError):
                        pass
            # gather from room and npc prototypes
            room_protos = load_all_prototypes("room")
            npc_protos = load_all_prototypes("npc")
            for proto in room_protos.values():
                name = proto.get("area")
                if not name:
                    continue
                info = area_data.setdefault(name, {"room_ids": [], "room_count": 0, "mob_count": 0})
                info["room_count"] += 1
                room_id = proto.get("room_id")
                if room_id is not None:
                    try:
                        info["room_ids"].append(int(room_id))
                    except (TypeError, ValueError):
                        pass
            for proto in npc_protos.values():
                name = proto.get("area")
                if not name:
                    continue
                info = area_data.setdefault(name, {"room_ids": [], "room_count": 0, "mob_count": 0})
                info["mob_count"] += 1
            for name, info in area_data.items():
                room_ids = sorted(
                    {rid for rid in info["room_ids"] if rid is not None}
                )
                start = min(room_ids) if room_ids else 0
                end = max(room_ids) if room_ids else 0
                area = Area(key=name, start=start, end=end)
                area._temp_room_count = info["room_count"]
                area._temp_mob_count = info["mob_count"]
                area._temp_room_ids = room_ids
                areas.append(area)
            if not areas:
                self.msg("No areas defined.")
                return
        table = EvTable(
            "Name",
            "Range",
            "Rooms",
            "Vnums",
            "Mobs",
            "Mob Spawns",
            "Builders",
            "Flags",
            "Age",
            "Interval",
            border="cells",
        )
        for area in areas:
            if hasattr(area, "_temp_room_count"):
                room_count = area._temp_room_count
                mob_count = area._temp_mob_count
                room_ids = getattr(area, "_temp_room_ids", [])
            else:
                if area.rooms:
                    room_ids = sorted(set(area.rooms))
                    room_count = len(room_ids)
                else:
                    objs = ObjectDB.objects.filter(
                        db_attributes__db_key="area",
                        db_attributes__db_strvalue__iexact=area.key,
                    )
                    rooms = [
                        obj for obj in objs if obj.is_typeclass(Room, exact=False)
                    ]
                    room_count = len(rooms)
                    room_ids = []
                    for room in rooms:
                        rid = room.attributes.get("room_id")
                        if rid is not None:
                            try:
                                room_ids.append(int(rid))
                            except (TypeError, ValueError):
                                pass
                    room_ids = sorted(set(room_ids))
                mob_count = len(area_npcs.get_area_npc_list(area.key))
                area._temp_room_ids = room_ids

            spawn_count = spawn_counts.get(area.key.lower(), 0)
            table.add_row(
                area.key,
                f"{area.start}-{area.end}",
                str(room_count),
                ", ".join(str(r) for r in room_ids) if room_ids else "-",
                str(mob_count),
                str(spawn_count),
                ", ".join(area.builders),
                ", ".join(area.flags),
                str(area.age),
                str(area.reset_interval),
            )
        self.msg(str(table))


class CmdASave(Command):
    """Save changed areas."""

    key = "asave"
    locks = "cmd:perm(Builder)"
    help_category = "Building"

    def func(self):
        if self.args.strip().lower() != "changed":
            self.msg("Usage: asave changed")
            return
        from commands.redit import proto_from_room
        from utils.prototype_manager import save_prototype
        updated = 0
        for idx, area in enumerate(get_areas()):
            for room_vnum in area.rooms:
                objs = ObjectDB.objects.filter(
                    db_attributes__db_key="room_id",
                    db_attributes__db_value=room_vnum,
                )
                room = next(
                    (o for o in objs if o.is_typeclass(Room, exact=False)), None
                )
                if not room:
                    continue
                proto = proto_from_room(room)
                save_prototype("room", proto, vnum=room_vnum)
                updated += 1
            update_area(idx, area)
        self.msg(f"All areas saved. {updated} room prototypes updated.")


class CmdAEdit(Command):
    """Edit or create area metadata."""

    key = "aedit"
    locks = "cmd:perm(Builder)"
    help_category = "Building"

    def func(self):
        if not self.args:
            self.msg(
                "Usage: aedit create <name> <start> <end> | "
                "aedit range <name> <start> <end> | "
                "aedit builders <name> <list> | aedit flags <name> <list> | "
                "aedit interval <name> <ticks>"
            )
            return
        parts = self.args.split(None, 1)
        sub = parts[0].lower()
        rest = parts[1].strip() if len(parts) > 1 else ""
        if sub == "create":
            args = rest.split()
            if len(args) != 3 or not args[1].isdigit() or not args[2].isdigit():
                self.msg("Usage: aedit create <name> <start> <end>")
                return
            name = args[0]
            start_val, end_val = int(args[1]), int(args[2])
            for warn in AreaValidator().validate({"start": start_val, "end": end_val}):
                self.msg(warn)
            start, end = min(start_val, end_val), max(start_val, end_val)
            if find_area(name)[1]:
                self.msg("Area already exists.")
                return
            area = Area(key=name, start=min(start, end), end=max(start, end))
            save_area(area)
            self.msg(f"Area {name} created.")
            return
        if sub == "range":
            args = rest.split()
            if len(args) != 3 or not args[1].isdigit() or not args[2].isdigit():
                self.msg("Usage: aedit range <name> <start> <end>")
                return
            name = args[0]
            idx, area = find_area(name)
            if area is None:
                self.msg(
                    f"Area '{name}' not found. Use 'alist' to view available areas."
                )
                return
            start_val, end_val = int(args[1]), int(args[2])
            for warn in AreaValidator().validate({"start": start_val, "end": end_val}):
                self.msg(warn)
            start, end = min(start_val, end_val), max(start_val, end_val)
            areas = get_areas()
            for other in areas:
                if other.key.lower() == area.key.lower():
                    continue
                if not (end < other.start or start > other.end):
                    self.msg(
                        f"Area '{name}' range overlaps with {other.key} ({other.start}-{other.end})"
                    )
                    return
            area.start = start
            area.end = end
            update_area(idx, area)
            self.msg("Range updated.")
            return
        if sub == "builders":
            args = rest.split(None, 1)
            if len(args) != 2:
                self.msg("Usage: aedit builders <name> <builders>")
                return
            name, builders = args[0], args[1]
            idx, area = find_area(name)
            if area is None:
                self.msg(
                    f"Area '{name}' not found. Use 'alist' to view available areas."
                )
                return
            area.builders = [b.strip() for b in builders.split(',') if b.strip()]
            update_area(idx, area)
            self.msg("Builders updated.")
            return
        if sub == "interval":
            args = rest.split()
            if len(args) != 2 or not args[1].isdigit():
                self.msg("Usage: aedit interval <name> <ticks>")
                return
            name, val = args[0], int(args[1])
            idx, area = find_area(name)
            if area is None:
                self.msg(
                    f"Area '{name}' not found. Use 'alist' to view available areas."
                )
                return
            area.reset_interval = val
            update_area(idx, area)
            self.msg("Reset interval updated.")
            return
        if sub == "flags":
            args = rest.split(None, 1)
            if len(args) != 2:
                self.msg("Usage: aedit flags <name> <flags>")
                return
            name, flags = args[0], args[1]
            idx, area = find_area(name)
            if area is None:
                self.msg(
                    f"Area '{name}' not found. Use 'alist' to view available areas."
                )
                return
            area.flags = [f.strip().lower() for f in flags.split(',') if f.strip()]
            update_area(idx, area)
            self.msg("Flags updated.")
            return
        if sub == "add":
            args = rest.split()
            if len(args) != 2 or not args[1].isdigit():
                self.msg("Usage: aedit add <area> <room_vnum>")
                return
            area_arg, vnum_str = args
            room_vnum = int(vnum_str)
            area = parse_area_identifier(area_arg)
            if area:
                idx, _ = find_area(area.key)
            else:
                idx = -1
            if area is None:
                self.msg(
                    f"Area '{area_arg}' not found. Use 'alist' to view available areas."
                )
                return
            proto = load_prototype("room", room_vnum)
            if not proto:
                self.msg("Room prototype not found.")
                return

            proto["area"] = area.key
            proto.setdefault("room_id", room_vnum)

            if room_vnum not in area.rooms:
                area.rooms.append(room_vnum)
            out_of_range = not (area.start <= room_vnum <= area.end)
            if out_of_range:
                self.msg(
                    f"Warning: room {room_vnum} outside {area.key} range {area.start}-{area.end}."
                )
                if room_vnum < area.start:
                    area.start = room_vnum
                if room_vnum > area.end:
                    area.end = room_vnum

            save_prototype("room", proto, vnum=room_vnum)

            update_area(idx, area)
            self.msg(f"Room {room_vnum} added to {area.key}.")
            return
        self.msg("Unknown subcommand.")


class CmdAreaReset(Command):
    """Reset an area's age."""

    key = "reset"
    locks = "cmd:perm(Builder)"
    help_category = "Building"

    def func(self):
        if not self.args:
            self.msg("Usage: reset <area>")
            return
        area_name = self.args.strip()
        idx, area = find_area(area_name)
        if area is None:
            self.msg(
                f"Area '{area_name}' not found. Use 'alist' to view available areas."
            )
            return
        area.age = 0
        update_area(idx, area)
        self.msg(f"{area.key} reset.")


class CmdAreaAge(Command):
    """Show an area's age."""

    key = "age"
    locks = "cmd:perm(Builder)"
    help_category = "Building"

    def func(self):
        area_name = self.args.strip()
        if not area_name and self.caller.location:
            area_name = self.caller.location.db.area or ""
        if not area_name:
            self.msg("Usage: age <area>")
            return
        _, area = find_area(area_name)
        if area is None:
            self.msg(
                f"Area '{area_name}' not found. Use 'alist' to view available areas."
            )
            return
        self.msg(f"{area.key} age: {area.age}")


class AreaEditCmdSet(CmdSet):
    """CmdSet adding area editing commands."""

    key = "AreaEditCmdSet"

    def at_cmdset_creation(self):
        super().at_cmdset_creation()
        self.add(CmdAList)
        self.add(CmdASave)
        self.add(CmdAEdit)
        self.add(CmdAreaReset)
        self.add(CmdAreaAge)

