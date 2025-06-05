from evennia.objects.models import ObjectDB
from evennia.utils.evtable import EvTable
from evennia import CmdSet

from .command import Command
from world.areas import Area, get_areas, save_area, update_area, find_area


class CmdAreas(Command):
    """List all registered areas."""

    key = "alist"
    aliases = ("areas",)
    locks = "cmd:perm(Builder)"
    help_category = "Building"

    def func(self):
        areas = get_areas()
        if not areas:
            self.msg("No areas registered.")
            return
        table = EvTable("Name", "Range", border="cells")
        for area in areas:
            table.add_row(area.key, f"{area.start}-{area.end}")
        self.msg(str(table))


class CmdAMake(Command):
    """Register a new area."""

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
    """Update an existing area's info."""

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
    """List rooms in the current area."""

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


class CmdRName(Command):
    """Rename the current room."""

    key = "rname"
    locks = "cmd:perm(Builder)"
    help_category = "Building"

    def func(self):
        if not self.args:
            self.msg("Usage: rname <new name>")
            return
        room = self.caller.location
        if not room:
            self.msg("You have no location.")
            return
        new_name = self.args.strip()
        room.key = new_name
        self.msg(f"Room renamed to {new_name}.")


class AreaCmdSet(CmdSet):
    key = "Area CmdSet"

    def at_cmdset_creation(self):
        super().at_cmdset_creation()
        self.add(CmdAreas)
        self.add(CmdAMake)
        self.add(CmdASet)
        self.add(CmdRooms)
        self.add(CmdRName)
