from evennia.objects.models import ObjectDB
from evennia.utils.evtable import EvTable
from evennia import CmdSet
from evennia.prototypes import spawner
from utils.script_utils import get_spawn_manager, respawn_area

from .command import Command, MuxCommand
from world.areas import (
    Area,
    get_areas,
    save_area,
    update_area,
    find_area,
    parse_area_identifier,
)
from .aedit import CmdAEdit, CmdAList, CmdASave, CmdAreaReset, CmdAreaAge
from typeclasses.rooms import Room
from utils.prototype_manager import load_prototype, load_all_prototypes


class CmdAMake(Command):
    """
    Register a new area. Usage: amake <name> <start>-<end>

    Usage:
        amake

    See |whelp amake|n for details.
    """

    key = "amake"
    locks = "cmd:perm(Builder)"
    help_category = "Building"

    def func(self):
        if not self.args:
            self.msg("Usage: amake <name> <start>-<end>")
            return
        try:
            name, rng = self.args.split(None, 1)
        except ValueError:
            self.msg("Usage: amake <name> <start>-<end>")
            return
        try:
            start, end = [int(x) for x in rng.split("-", 1)]
        except ValueError:
            self.msg("Range must be two integers joined by '-'")
            return
        if start > end:
            start, end = end, start
        areas = get_areas()
        for area in areas:
            if not (end < area.start or start > area.end):
                gaps: list[tuple[int, int | None]] = []
                sorted_areas = sorted(areas, key=lambda a: a.start)
                prev_end: int | None = None
                for ar in sorted_areas:
                    if prev_end is None:
                        if ar.start > 1:
                            gaps.append((1, ar.start - 1))
                    else:
                        if ar.start > prev_end + 1:
                            gaps.append((prev_end + 1, ar.start - 1))
                    prev_end = max(prev_end if prev_end is not None else ar.end, ar.end)
                if prev_end is not None:
                    gaps.append((prev_end + 1, None))

                range_strs = []
                for s, e in gaps:
                    if e is None:
                        range_strs.append(f"{s}-")
                    else:
                        range_strs.append(f"{s}-{e}")

                self.msg(
                    f"Range overlaps with {area.key} ({area.start}-{area.end}). "
                    f"Available ranges: {', '.join(range_strs)}"
                )
                return
        new_area = Area(key=name, start=start, end=end)
        save_area(new_area)
        # tag the current room as the first room of this area
        if location := self.caller.location:
            location.set_area(name, start)
        self.msg(f"Area '{name}' registered for rooms {start}-{end}.")


class CmdASet(Command):
    """
    Update an area's properties. Usage: aset <area> <name|range|desc> <value>

    Usage:
        aset

    See |whelp aset|n for details.
    """

    key = "aset"
    locks = "cmd:perm(Builder)"
    help_category = "Building"

    def func(self):
        if not self.args:
            self.msg("Usage: aset <area> <property> <value>")
            return
        parts = self.args.split(None, 2)
        if len(parts) < 3:
            self.msg("Usage: aset <area> <property> <value>")
            return
        area_name, prop, value = parts
        idx, area = find_area(area_name)
        if area is None:
            self.msg(
                f"Area '{area_name}' not found. Use 'alist' to view available areas."
            )
            return
        prop = prop.lower()
        if prop in ("name", "key"):
            area.key = value
        elif prop in ("range",):
            try:
                start, end = [int(x) for x in value.split("-", 1)]
            except ValueError:
                self.msg("Range must be two integers joined by '-'")
                return
            if start > end:
                start, end = end, start
            areas = get_areas()
            for other in areas:
                if other is area:
                    continue
                if not (end < other.start or start > other.end):
                    self.msg(
                        f"Range overlaps with {other.key} ({other.start}-{other.end})"
                    )
                    return
            area.start = start
            area.end = end
        elif prop in ("desc", "description"):
            area.desc = value
        else:
            self.msg("Unknown property. Use name, range or desc.")
            return
        update_area(idx, area)
        self.msg(f"Area '{area.key}' updated.")


class CmdRooms(Command):
    """
    Show rooms belonging to your current area.

    Usage:
        rooms

    See |whelp rooms|n for details.
    """

    key = "rooms"
    aliases = ("roomsall",)
    locks = "cmd:perm(Builder)"
    help_category = "Building"

    def func(self):
        location = self.caller.location
        if not location:
            self.msg("You have no location.")
            return
        areas = get_areas()
        current = None
        for area in areas:
            if area.start <= location.id <= area.end:
                current = area
                break
        if not current:
            self.msg("This room is not within a registered area.")
            return
        objs = ObjectDB.objects.filter(id__gte=current.start, id__lte=current.end)
        rooms = {obj.id: obj for obj in objs if obj.is_typeclass("evennia.objects.objects.DefaultRoom", exact=False)}
        show_all = self.cmdstring.lower() == "roomsall"
        lines = []
        for num in range(current.start, current.end + 1):
            if num in rooms:
                lines.append(f"{num}: {rooms[num].key}")
            elif show_all:
                lines.append(f"{num}: (unbuilt)")
        header = f"Rooms in {current.key} ({current.start}-{current.end})"
        self.msg("\n".join([header] + lines))


class CmdRList(Command):
    """List rooms in an area."""

    key = "rlist"
    locks = "cmd:perm(Builder)"
    help_category = "Building"

    def func(self):
        area_name = self.args.strip()
        if not area_name:
            location = self.caller.location
            if not location:
                self.msg("Usage: rlist <area>")
                return
            if not location.db.area:
                self.msg("No area information found for this room.")
                return
            area_name = location.db.area

        idx, area = find_area(area_name)
        if area is None:
            self.msg(
                f"Area '{area_name}' not found. Use 'alist' to view available areas."
            )
            return

        objs = ObjectDB.objects.filter(
            db_attributes__db_key="area",
            db_attributes__db_strvalue__iexact=area.key,
        )
        rooms = {
            (obj.db.room_id if obj.db.room_id is not None else obj.id): obj
            for obj in objs
            if obj.is_typeclass(Room, exact=False)
        }

        protos = load_all_prototypes("room")
        proto_nums = set()
        for num, proto in protos.items():
            proto_area = proto.get("area")
            if proto_area and proto_area.lower() == area.key.lower():
                rid = proto.get("room_id", num)
                try:
                    proto_nums.add(int(rid))
                except (TypeError, ValueError):
                    continue

        vnums = set(area.rooms) | set(rooms.keys()) | proto_nums
        if not vnums:
            self.msg(f"No rooms found in {area_name}.")
            return

        lines = []
        for num in sorted(vnums):
            if num in rooms:
                lines.append(f"{num}: {rooms[num].key}")
            else:
                lines.append(f"{num}: (unbuilt)")

        header = f"Rooms in {area.key} ({area.start}-{area.end})"
        self.msg("\n".join([header] + lines))


class CmdRMake(MuxCommand):
    """Create an unlinked room in a registered area."""

    key = "rmake"
    locks = "cmd:perm(Builder)"
    help_category = "Building"

    def func(self):
        force = False
        if "--force" in self.switches:
            force = True
            self.switches.remove("--force")

        if not self.args:
            self.msg("Usage: rmake <area> <number>")
            return

        parts = self.args.split()
        if len(parts) != 2 or not parts[1].isdigit():
            self.msg("Usage: rmake <area> <number>")
            return

        area_name, num_str = parts
        room_id = int(num_str)

        area = parse_area_identifier(area_name)
        if area:
            idx, _ = find_area(area.key)
        else:
            idx = -1
        if area is None:
            self.msg(
                f"Area '{area_name}' not found. Use 'alist' to view available areas."
            )
            return

        if not (area.start <= room_id <= area.end):
            self.msg("Number outside area range.")
            return

        proto = load_prototype("room", room_id)
        if proto is None:
            self.msg(f"Room prototype {room_id} not found.")
            return

        objs = ObjectDB.objects.filter(
            db_attributes__db_key="area",
            db_attributes__db_strvalue__iexact=area.key,
        )
        existing = None
        for obj in objs:
            if obj.db.room_id == room_id and obj.is_typeclass(Room, exact=False):
                existing = obj
                break

        if existing:
            if force:
                existing.delete()
            else:
                self.msg("Room already exists.")
                return

        new_room = spawner.spawn(proto)[0]
        new_room.set_area(area.key, room_id)
        if room_id not in area.rooms:
            area.rooms.append(room_id)
        update_area(idx, area)

        self.msg(f"Room {room_id} created in area {area.key}.")


class CmdRName(Command):
    """
    Rename the room you are currently in.

    Usage:
        rrename <new name>

    See |whelp rrename|n for details.
    """

    key = "rrename"
    aliases = ("roomrename", "renameroom", "rname")
    locks = "cmd:perm(Builder)"
    help_category = "Building"

    def func(self):
        if not self.args:
            self.msg("Usage: rrename <new name>")
            return
        room = self.caller.location
        if not room:
            self.msg("You have no location.")
            return
        new_name = self.args.strip()
        room.key = new_name
        self.msg(f"Room renamed to {new_name}.")


class CmdRDesc(Command):
    """
    View or change the current room's description.

    Usage:
        rdesc <new description>

    See |whelp rdesc|n for details.
    """

    key = "rdesc"
    aliases = ("roomdesc",)
    locks = "cmd:perm(Builder)"
    help_category = "Building"

    def func(self):
        room = self.caller.location
        if not room:
            self.msg("You have no location.")
            return
        if not self.args:
            desc = room.db.desc or "This room has no description."
            self.msg(desc)
        else:
            room.db.desc = self.args.strip()
            self.msg("Room description updated.")


class CmdRSet(Command):
    """
    Set properties on the current room.

    Usage:
        rset area <area name>
        rset id <number>

    See |whelp rset|n for details.
    """

    key = "rset"
    locks = "cmd:perm(Builder)"
    help_category = "Building"

    def func(self):
        if not self.args:
            self.msg("Usage: rset <area|id> <value>")
            return
        room = self.caller.location
        if not room:
            self.msg("You have no location.")
            return
        parts = self.args.split(None, 1)
        if len(parts) < 2:
            self.msg("Usage: rset <area|id> <value>")
            return
        prop, value = parts
        prop = prop.lower()
        if prop == "area":
            area_name = value.strip()
            _, area = find_area(area_name)
            if area is None:
                self.msg(
                    f"Area '{area_name}' not found. Use 'alist' to view available areas."
                )
                return
            room.set_area(area_name)
            self.msg(f"Room assigned to area {area_name}.")
        elif prop == "id":
            if not value.isdigit():
                self.msg("Room id must be numeric.")
                return
            room_id = int(value)
            area = room.db.area
            if not area:
                self.msg("This room has no area.")
                return
            _, area_data = find_area(area)
            if area_data and not (area_data.start <= room_id <= area_data.end):
                self.msg("Number outside area range.")
                return
            objs = ObjectDB.objects.filter(
                db_attributes__db_key="area",
                db_attributes__db_strvalue__iexact=area,
            )
            for obj in objs:
                if obj == room:
                    continue
                if obj.db.room_id == room_id:
                    self.msg("Room already exists.")
                    return
            room.db.room_id = room_id
            self.msg(f"Room id set to {room_id}.")
        else:
            self.msg("Usage: rset <area|id> <value>")


class CmdRReg(Command):
    """Assign a room to an area and number."""

    key = "rreg"
    locks = "cmd:perm(Builder)"
    help_category = "Building"

    def func(self):
        if not self.args:
            self.msg("Usage: rreg <area> <number> | rreg <room> <area> <number>")
            return

        parts = self.args.split()
        if len(parts) == 2:
            area_name, num_str = parts
            room = self.caller.location
        elif len(parts) == 3:
            room_name, area_name, num_str = parts
            room = self.caller.search_first(room_name, global_search=True)
            if not room:
                return
            if not room.is_typeclass(Room, exact=False):
                self.msg("Target must be a room.")
                return
        else:
            self.msg("Usage: rreg <area> <number> | rreg <room> <area> <number>")
            return

        if not num_str.isdigit():
            self.msg("Number must be numeric.")
            return
        room_id = int(num_str)

        area = parse_area_identifier(area_name)
        if area:
            idx, _ = find_area(area.key)
        else:
            idx = -1
        if area is None:
            self.msg(
                f"Area '{area_name}' not found. Use 'alist' to view available areas."
            )
            return
        if not (area.start <= room_id <= area.end):
            self.msg("Number outside area range.")
            return

        objs = ObjectDB.objects.filter(
            db_attributes__db_key="area",
            db_attributes__db_strvalue__iexact=area_name,
        )
        for obj in objs:
            if obj == room:
                continue
            if obj.db.room_id == room_id and obj.is_typeclass(Room, exact=False):
                self.msg("Room already exists.")
                return

        room.set_area(area.key, room_id)
        if room_id not in area.rooms:
            area.rooms.append(room_id)
            update_area(idx, area)
        name = room.key if room != self.caller.location else "Room"
        self.msg(f"{name} registered as {area.key} #{room_id}.")


class CmdRRegAll(Command):
    """Spawn and register all room prototypes."""

    key = "rregall"
    locks = "cmd:perm(Builder)"
    help_category = "Building"

    def func(self):
        created = 0
        protos = load_all_prototypes("room")
        for vnum, proto in protos.items():
            area_name = proto.get("area")
            if not area_name:
                continue
            idx, area = find_area(area_name)
            if area is None:
                continue
            room_id = int(vnum)
            objs = ObjectDB.objects.filter(
                db_attributes__db_key="area",
                db_attributes__db_strvalue__iexact=area_name,
            )
            exists = False
            for obj in objs:
                if obj.db.room_id == room_id and obj.is_typeclass(Room, exact=False):
                    exists = True
                    break
            if exists:
                continue

            new_room = spawner.spawn(proto)[0]
            new_room.set_area(area_name, room_id)
            if room_id not in area.rooms:
                area.rooms.append(room_id)
            update_area(idx, area)
            created += 1

        self.msg(f"Created {created} room{'s' if created != 1 else ''}.")


class CmdAreasReset(Command):
    """Repopulate spawn entries for an area."""

    key = "areas.reset"
    locks = "cmd:perm(Builder)"
    help_category = "Building"

    def func(self):
        if not self.args:
            self.msg("Usage: areas.reset <area>")
            return
        area_name = self.args.strip()
        _, area = find_area(area_name)
        if area is None:
            self.msg(
                f"Area '{area_name}' not found. Use 'alist' to view available areas."
            )
            return
        script = get_spawn_manager()
        if not script or not hasattr(script, "force_respawn"):
            self.msg("Spawn manager not found.")
            return
        respawn_area(area.key.lower())
        self.msg(f"Spawn entries reset for {area.key}.")


class AreaCmdSet(CmdSet):
    key = "Area CmdSet"

    def at_cmdset_creation(self):
        super().at_cmdset_creation()
        self.add(CmdAList)
        self.add(CmdASave)
        self.add(CmdAEdit)
        self.add(CmdAreaReset)
        self.add(CmdAreaAge)
        self.add(CmdAreasReset)
        self.add(CmdAMake)
        self.add(CmdASet)
        self.add(CmdRooms)
        self.add(CmdRList)
        self.add(CmdRMake)
        self.add(CmdRName)
        self.add(CmdRDesc)
        self.add(CmdRSet)
        self.add(CmdRReg)
        self.add(CmdRRegAll)
        from .redit import CmdREdit
        self.add(CmdREdit)



