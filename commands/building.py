from evennia import create_object
from .command import Command
from typeclasses.rooms import Room
from typeclasses.exits import Exit


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
        args = self.args.strip().split()
        if not args:
            caller.msg("Usage: dig <direction> [area] [number]")
            return
        direction = DIR_FULL.get(args[0].lower())
        if not direction:
            caller.msg("Unknown direction.")
            return
        area = args[1] if len(args) > 1 else caller.location.db.area
        room_id = None
        if len(args) > 2:
            if args[2].isdigit():
                room_id = int(args[2])
            else:
                caller.msg("Room id must be numeric.")
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
