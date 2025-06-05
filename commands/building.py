from evennia import create_object
from evennia.objects.models import ObjectDB
from .command import Command
from typeclasses.rooms import Room
from typeclasses.exits import Exit
from world.areas import find_area


DIR_FULL = {
    "n": "north",
    "north": "north",
    "s": "south",
    "south": "south",
    "e": "east",
    "east": "east",
    "w": "west",
    "west": "west",
    "ne": "northeast",
    "northeast": "northeast",
    "nw": "northwest",
    "northwest": "northwest",
    "se": "southeast",
    "southeast": "southeast",
    "sw": "southwest",
    "southwest": "southwest",
    "u": "up",
    "up": "up",
    "d": "down",
    "down": "down",
    "i": "in",
    "in": "in",
    "o": "out",
    "out": "out",
}

OPPOSITE = {
    "north": "south",
    "south": "north",
    "east": "west",
    "west": "east",
    "northeast": "southwest",
    "southwest": "northeast",
    "northwest": "southeast",
    "southeast": "northwest",
    "up": "down",
    "down": "up",
    "in": "out",
    "out": "in",
}

SHORT = {
    "north": "n",
    "south": "s",
    "east": "e",
    "west": "w",
    "northeast": "ne",
    "southwest": "sw",
    "northwest": "nw",
    "southeast": "se",
    "up": "u",
    "down": "d",
    "in": "i",
    "out": "o",
}


class CmdDig(Command):
    """Dig a new room in a direction."""

    key = "dig"
    locks = "cmd:perm(Builder)"
    help_category = "Building"

    def func(self):
        caller = self.caller
        argstr = self.args.strip()
        if not argstr:
            caller.msg("Usage: dig <direction>=<area>:<number>")
            return
        area = caller.location.db.area
        room_id = None

        if "=" in argstr:
            dir_part, rhs = (p.strip() for p in argstr.split("=", 1))
            direction = DIR_FULL.get(dir_part.lower())
            if not direction:
                caller.msg("Unknown direction.")
                return
            if ":" in rhs:
                area_part, num_part = (p.strip() for p in rhs.split(":", 1))
                if area_part:
                    area = area_part
                if num_part:
                    if num_part.isdigit():
                        room_id = int(num_part)
                    else:
                        caller.msg("Room id must be numeric.")
                        return
            else:
                if rhs:
                    area = rhs
        else:
            parts = argstr.split()
            direction = DIR_FULL.get(parts[0].lower())
            if not direction:
                caller.msg("Unknown direction.")
                return
            if len(parts) > 1:
                area = parts[1]
            if len(parts) > 2:
                if parts[2].isdigit():
                    room_id = int(parts[2])
                else:
                    caller.msg("Room id must be numeric.")
                    return

        if area:
            _, area_data = find_area(area)
            if area_data:
                if room_id is not None and not (area_data.start <= room_id <= area_data.end):
                    caller.msg("Number outside area range.")
                    return
            if room_id is not None:
                objs = ObjectDB.objects.filter(db_attributes__db_key="area", db_attributes__db_strvalue__iexact=area)
                for obj in objs:
                    if obj.db.room_id == room_id:
                        caller.msg("Room already exists.")
                        return
        opposite = OPPOSITE[direction]

        new_room = create_object(Room, key="Room")
        if area:
            new_room.set_area(area, room_id)
        exit_to = create_object(
            Exit,
            key=direction,
            aliases=[SHORT[direction]],
            location=caller.location,
            destination=new_room,
        )
        exit_back = create_object(
            Exit,
            key=opposite,
            aliases=[SHORT[opposite]],
            location=new_room,
            destination=caller.location,
        )
        caller.msg(f"You dig {direction} and create a new room.")


class CmdTeleport(Command):
    """Teleport to a room using ``<area>:<number>``."""

    key = "@teleport"
    locks = "cmd:perm(Builder)"
    help_category = "Building"

    def func(self):
        if not self.args:
            self.msg("Usage: @teleport <area>:<number>")
            return

        area_part, sep, num_part = self.args.strip().partition(":")
        if not sep or not area_part or not num_part:
            self.msg("Usage: @teleport <area>:<number>")
            return
        if not num_part.isdigit():
            self.msg("Room number must be numeric.")
            return
        room_id = int(num_part)
        _, area = find_area(area_part)
        if area:
            if not (area.start <= room_id <= area.end):
                self.msg("Number outside area range.")
                return
        objs = ObjectDB.objects.filter(db_attributes__db_key="area", db_attributes__db_strvalue__iexact=area_part)
        room = None
        for obj in objs:
            if obj.db.room_id == room_id and obj.is_typeclass(Room, exact=False):
                room = obj
                break
        if not room:
            self.msg("That room does not exist.")
            return
        self.caller.move_to(room, quiet=True, move_type="teleport")
        self.msg(f"Teleported to {room.get_display_name(self.caller)}.")
