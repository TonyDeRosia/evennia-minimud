from evennia.objects.models import ObjectDB
from evennia.utils.evtable import EvTable
from evennia import CmdSet, create_object

from .command import Command
from scripts.area_spawner import AreaSpawner
from world.areas import Area, get_areas, save_area, update_area, find_area
from .aedit import CmdAEdit, CmdAList, CmdASave, CmdAreaReset, CmdAreaAge
from typeclasses.rooms import Room


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
                self.msg(f"Range overlaps with {area.key} ({area.start}-{area.end})")
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
            self.msg("Unknown area.")
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

        _, area = find_area(area_name)
        if area is None:
            self.msg("Unknown area.")
            return

        objs = ObjectDB.objects.filter(
            db_attributes__db_key="area",
            db_attributes__db_strvalue__iexact=area_name,
        )
        rooms = [obj for obj in objs if obj.is_typeclass(Room, exact=False)]
        if not rooms:
            self.msg(f"No rooms found in {area_name}.")
            return

        lines = []
        for room in sorted(
            rooms, key=lambda r: r.db.room_id if r.db.room_id is not None else r.id
        ):
            num = room.db.room_id if room.db.room_id is not None else room.id
            lines.append(f"{num}: {room.key}")

        header = f"Rooms in {area_name}"
        self.msg("\n".join([header] + lines))


class CmdRMake(Command):
    """Create an unlinked room in a registered area."""

    key = "rmake"
    locks = "cmd:perm(Builder)"
    help_category = "Building"

    def func(self):
        if not self.args:
            self.msg("Usage: rmake <area> <number>")
            return
        parts = self.args.split()
        if len(parts) != 2 or not parts[1].isdigit():
            self.msg("Usage: rmake <area> <number>")
            return
        area_name, num_str = parts
        room_id = int(num_str)
        _, area = find_area(area_name)
        if area is None:
            self.msg("Unknown area.")
            return
        if not (area.start <= room_id <= area.end):
            self.msg("Number outside area range.")
            return
        objs = ObjectDB.objects.filter(
            db_attributes__db_key="area",
            db_attributes__db_strvalue__iexact=area_name,
        )
        for obj in objs:
            if obj.db.room_id == room_id and obj.is_typeclass(Room, exact=False):
                self.msg("Room already exists.")
                return
        new_room = create_object(Room, key="Room")
        new_room.set_area(area_name, room_id)
        self.msg(f"Room {room_id} created in area {area_name}.")


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
            area = value.strip()
            room.set_area(area)
            self.msg(f"Room assigned to area {area}.")
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
            room = self.caller.search(room_name, global_search=True)
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

        _, area = find_area(area_name)
        if area is None:
            self.msg("Unknown area.")
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

        room.set_area(area_name, room_id)
        name = room.key if room != self.caller.location else "Room"
        self.msg(f"{name} registered as {area_name} #{room_id}.")


class AreaCmdSet(CmdSet):
    key = "Area CmdSet"

    def at_cmdset_creation(self):
        super().at_cmdset_creation()
        self.add(CmdAList)
        self.add(CmdASave)
        self.add(CmdAEdit)
        self.add(CmdAreaReset)
        self.add(CmdAreaAge)
        self.add(CmdAMake)
        self.add(CmdASet)
        self.add(CmdRooms)
        self.add(CmdRList)
        self.add(CmdRMake)
        self.add(CmdRName)
        self.add(CmdRDesc)
        self.add(CmdRSet)
        self.add(CmdRReg)
        self.add(CmdRSpawner)
        from .redit import CmdREdit
        self.add(CmdREdit)



class CmdRSpawner(Command):
    """Configure NPC respawning for the current room."""

    key = "@rspawner"
    locks = "cmd:perm(Builder)"
    help_category = "Building"

    def func(self):
        room = self.caller.location
        if not room:
            self.msg("You have no location.")
            return
        if not self.args:
            script = room.scripts.get("area_spawner")
            if not script:
                self.msg("No AreaSpawner on this room.")
                return
            script = script[0]
            self.msg(
                f"Interval: {script.db.respawn_interval}s, Max: {script.db.max_population}, Chance: {script.db.spawn_chance}%"
            )
            return
        parts = self.args.split(None, 1)
        if len(parts) != 2:
            self.msg("Usage: @rspawner <interval|max|chance> <value>")
            return
        field, value = parts
        script = room.scripts.get("area_spawner")
        if not script:
            script = room.scripts.add(AreaSpawner, key="area_spawner")
        else:
            script = script[0]
        field = field.lower()
        if field in ("interval", "respawn_interval"):
            try:
                val = int(value)
            except ValueError:
                self.msg("Interval must be an integer.")
                return
            script.db.respawn_interval = val
            script.interval = val
        elif field in ("max", "max_population"):
            try:
                val = int(value)
            except ValueError:
                self.msg("Max population must be an integer.")
                return
            script.db.max_population = val
        elif field in ("chance", "spawn_chance"):
            try:
                val = int(value)
            except ValueError:
                self.msg("Chance must be an integer.")
                return
            val = max(0, min(val, 100))
            script.db.spawn_chance = val
        else:
            self.msg("Usage: @rspawner <interval|max|chance> <value>")
            return
        self.msg(f"Spawner {field} set to {val}.")
