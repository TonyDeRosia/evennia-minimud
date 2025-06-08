from evennia import CmdSet
from .command import Command

DIR_MAP = {
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


class MoveCommand(Command):
    direction = ""
    key = ""
    aliases = []
    locks = "cmd:all()"

    def func(self):
        dest_info = (self.caller.location.db.exits or {}).get(self.direction)
        if not dest_info:
            self.caller.msg("You cannot go that way.")
            return

        if isinstance(dest_info, dict):
            map_name = dest_info.get("wilderness_name")
            coords = dest_info.get("wilderness_coords")
            if map_name and coords:
                from evennia.contrib.grid.wilderness import wilderness
                if wilderness.enter_wilderness(self.caller, coordinates=coords, name=map_name):
                    return
                self.caller.msg("You cannot go that way.")
                return
            dest = dest_info.get("room")
        else:
            dest = dest_info

        if not dest:
            self.caller.msg("You cannot go that way.")
            return
        self.caller.move_to(dest, move_type="exit")


def create_move_command(name, aliases):
    return type(
        f"Cmd{name.capitalize()}",
        (MoveCommand,),
        {"direction": name, "key": name, "aliases": aliases},
    )


# generate commands for all directions
_move_cmds = [
    create_move_command("north", ["n"]),
    create_move_command("south", ["s"]),
    create_move_command("east", ["e"]),
    create_move_command("west", ["w"]),
    create_move_command("northeast", ["ne"]),
    create_move_command("northwest", ["nw"]),
    create_move_command("southeast", ["se"]),
    create_move_command("southwest", ["sw"]),
    create_move_command("up", ["u"]),
    create_move_command("down", ["d"]),
    create_move_command("in", ["i"]),
    create_move_command("out", ["o"]),
]


class MovementCmdSet(CmdSet):
    key = "MovementCmdSet"

    def at_cmdset_creation(self):
        super().at_cmdset_creation()
        for cmd in _move_cmds:
            self.add(cmd())

