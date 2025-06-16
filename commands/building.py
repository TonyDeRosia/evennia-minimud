from evennia import create_object
from evennia.objects.models import ObjectDB
from .command import Command
from typeclasses.rooms import Room
from world.areas import find_area
from utils import VALID_SLOTS, normalize_slot


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
    """
    Create a new room in a direction. Usage: dig <direction> [<area>:<number>]

    Usage:
        dig

    See |whelp dig|n for details.
    """

    key = "dig"
    locks = "cmd:perm(Builder) or perm(Admin) or perm(Developer)"
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

        # add exits in both directions
        caller.location.db.exits = caller.location.db.exits or {}
        new_room.db.exits = new_room.db.exits or {}
        caller.location.db.exits[direction] = new_room
        new_room.db.exits[opposite] = caller.location

        caller.msg(f"You dig {direction} and create a new room.")


class CmdTeleport(Command):
    """
    Teleport directly to a room. Usage: @teleport <area>:<number> or <number>

    Usage:
        @teleport
        tp

    See |whelp @teleport|n for details.
    """

    key = "@teleport"
    aliases = ["tp"]
    locks = "cmd:perm(Builder) or perm(Admin) or perm(Developer)"
    help_category = "Building"

    def func(self):
        if not self.args:
            self.msg("Usage: @teleport <area>:<number> or <number>")
            return

        args = self.args.strip()
        area_part: str | None = None
        room_id: int | None = None

        if args.isdigit():
            room_id = int(args)
            area = find_area_by_vnum(room_id)
            area_part = area.key if area else None
        else:
            area_part, sep, num_part = args.partition(":")
            if not sep or not area_part or not num_part:
                self.msg("Usage: @teleport <area>:<number> or <number>")
                return
            if not num_part.isdigit():
                self.msg("Room number must be numeric.")
                return
            room_id = int(num_part)
            _, area = find_area(area_part)
            if area and not (area.start <= room_id <= area.end):
                self.msg("Number outside area range.")
                return

        objs = ObjectDB.objects.filter(db_attributes__db_key="room_id", db_attributes__db_value=room_id)
        if area_part:
            objs = [obj for obj in objs if (obj.db.area or "").lower() == area_part.lower()]
        room = None
        for obj in objs:
            if obj.is_typeclass(Room, exact=False):
                room = obj
                break
        if not room:
            self.msg("That room does not exist.")
            return
        self.caller.move_to(room, quiet=True, move_type="teleport")
        self.msg(f"Teleported to {room.get_display_name(self.caller)}.")


class CmdDelDir(Command):
    """Delete an exit from the current room."""

    key = "deldir"
    locks = "cmd:perm(Builder) or perm(Admin) or perm(Developer)"
    help_category = "Building"

    def func(self):
        if not self.args:
            self.msg("Usage: deldir <direction>")
            return
        direction = DIR_FULL.get(self.args.strip().lower())
        if not direction:
            self.msg("Unknown direction.")
            return

        room = self.caller.location
        if not room:
            self.msg("You have no location.")
            return

        exits = room.db.exits or {}
        target = exits.get(direction)
        if not target:
            self.msg("No exit in that direction.")
            return

        # remove exit from current room
        exits.pop(direction, None)
        room.db.exits = exits

        # also remove the reverse exit if it points back here
        opposite = OPPOSITE.get(direction)
        if opposite and target.db.exits:
            back = target.db.exits.get(opposite)
            if back == room:
                other_exits = target.db.exits
                other_exits.pop(opposite, None)
                target.db.exits = other_exits

        self.msg(f"Exit {direction} removed.")


class CmdDelRoom(Command):
    """Delete a room and clean up linking exits."""

    key = "delroom"
    locks = "cmd:perm(Builder) or perm(Admin) or perm(Developer)"
    help_category = "Building"

    def unlink_room(self, room):
        """Remove any exits pointing to or from the room."""
        for other in ObjectDB.objects.filter(db_attributes__db_key="exits"):
            if not other.is_typeclass(Room, exact=False):
                continue
            exits = other.db.exits or {}
            changed = False
            for direc, target in list(exits.items()):
                if target == room:
                    exits.pop(direc, None)
                    changed = True
            if changed:
                other.db.exits = exits
        room.db.exits = {}

    def func(self):
        if not self.args:
            self.msg("Usage: delroom <direction>|<area> <number>")
            return

        parts = self.args.split()
        target_room = None

        if len(parts) == 1:
            direction = DIR_FULL.get(parts[0].lower())
            if not direction:
                self.msg("Unknown direction.")
                return
            current = self.caller.location
            if not current:
                self.msg("You have no location.")
                return
            target_room = (current.db.exits or {}).get(direction)
            if not target_room:
                self.msg("No room in that direction.")
                return
        else:
            if len(parts) != 2 or not parts[1].isdigit():
                self.msg("Usage: delroom <direction>|<area> <number>")
                return
            area, num = parts[0], int(parts[1])
            _, area_data = find_area(area)
            if area_data and not (area_data.start <= num <= area_data.end):
                self.msg("Number outside area range.")
                return
            objs = ObjectDB.objects.filter(
                db_attributes__db_key="area",
                db_attributes__db_strvalue__iexact=area,
            )
            for obj in objs:
                if obj.db.room_id == num and obj.is_typeclass(Room, exact=False):
                    target_room = obj
                    break
            if not target_room:
                self.msg("That room does not exist.")
                return

        self.unlink_room(target_room)
        target_room.delete()
        self.msg("Room deleted.")


class CmdSetDesc(Command):
    """
    Set an object's description. Usage: setdesc <target> <description>

    Usage:
        setdesc

    See |whelp setdesc|n for details.
    """

    key = "setdesc"
    locks = "cmd:perm(Admin) or perm(Builder)"
    help_category = "Building"

    def func(self):
        if not self.args:
            self.msg("Usage: setdesc <target> <description>")
            return
        target_name, *desc_parts = self.args.split(None, 1)
        if not desc_parts:
            self.msg("Usage: setdesc <target> <description>")
            return
        target = self.caller.search(target_name, global_search=True)
        if not target:
            return
        target.db.desc = desc_parts[0].strip()
        self.msg(f"Description set on {target.key}.")


class CmdSetWeight(Command):
    """
    Set an object's weight. Usage: setweight <target> <value>

    Usage:
        setweight

    See |whelp setweight|n for details.
    """

    key = "setweight"
    locks = "cmd:perm(Admin) or perm(Builder)"
    help_category = "Building"

    def func(self):
        if not self.args:
            self.msg("Usage: setweight <target> <value>")
            return
        parts = self.args.split(None, 1)
        if len(parts) != 2 or not parts[1].isdigit():
            self.msg("Usage: setweight <target> <value>")
            return
        target = self.caller.search(parts[0], global_search=True)
        if not target:
            return
        target.db.weight = int(parts[1])
        self.msg(f"Weight on {target.key} set to {parts[1]}.")


class CmdSetSlot(Command):
    """
    Define the slot or clothing type on an item. Usage: setslot <target> <slot>

    Usage:
        setslot

    See |whelp setslot|n for details.
    """

    key = "setslot"
    locks = "cmd:perm(Admin) or perm(Builder)"
    help_category = "Building"

    def func(self):
        if not self.args:
            self.msg("Usage: setslot <target> <slot>")
            return
        parts = self.args.split(None, 1)
        if len(parts) != 2:
            self.msg("Usage: setslot <target> <slot>")
            return
        target = self.caller.search(parts[0], global_search=True)
        if not target:
            return

        slot = normalize_slot(parts[1])
        if slot not in VALID_SLOTS:
            self.msg("Invalid slot name.")
            return

        target.db.slot = slot
        self.msg(f"Slot on {target.key} set to {slot}.")


class CmdSetDamage(Command):
    """
    Assign a damage value to a weapon. Usage: setdamage <target> <amount>

    Usage:
        setdamage

    See |whelp setdamage|n for details.
    """

    key = "setdamage"
    locks = "cmd:perm(Admin) or perm(Builder)"
    help_category = "Building"

    def func(self):
        if not self.args:
            self.msg("Usage: setdamage <target> <amount>")
            return
        parts = self.args.split(None, 1)
        if len(parts) != 2 or not parts[1].lstrip("-+").isdigit():
            self.msg("Usage: setdamage <target> <amount>")
            return
        target = self.caller.search(parts[0], global_search=True)
        if not target:
            return
        target.db.dmg = int(parts[1])
        self.msg(f"Damage on {target.key} set to {parts[1]}.")


class CmdSetBuff(Command):
    """
    Add a buff identifier to an object. Usage: setbuff <target> <buff>

    Usage:
        setbuff

    See |whelp setbuff|n for details.
    """

    key = "setbuff"
    locks = "cmd:perm(Admin) or perm(Builder)"
    help_category = "Building"

    def func(self):
        if not self.args:
            self.msg("Usage: setbuff <target> <buff>")
            return
        parts = self.args.split(None, 1)
        if len(parts) != 2:
            self.msg("Usage: setbuff <target> <buff>")
            return
        target = self.caller.search(parts[0], global_search=True)
        if not target:
            return
        target.db.buff = parts[1].strip()
        self.msg(f"Buff on {target.key} set to {parts[1].strip()}.")


class CmdSetFlag(Command):
    """Add a flag to an object."""

    key = "setflag"
    locks = "cmd:perm(Admin) or perm(Builder)"
    help_category = "Building"

    def func(self):
        if not self.args:
            self.msg("Usage: setflag <target> <flag>")
            return
        parts = self.args.split(None, 1)
        if len(parts) != 2:
            self.msg("Usage: setflag <target> <flag>")
            return
        target = self.caller.search(parts[0], global_search=True)
        if not target:
            return
        flag = parts[1].strip().lower()
        target.tags.add(flag, category="flag")
        self.msg(f"Flag {flag} set on {target.key}.")


class CmdRemoveFlag(Command):
    """Remove a flag from an object."""

    key = "removeflag"
    locks = "cmd:perm(Admin) or perm(Builder)"
    help_category = "Building"

    def func(self):
        if not self.args:
            self.msg("Usage: removeflag <target> <flag>")
            return
        parts = self.args.split(None, 1)
        if len(parts) != 2:
            self.msg("Usage: removeflag <target> <flag>")
            return
        target = self.caller.search(parts[0], global_search=True)
        if not target:
            return
        flag = parts[1].strip().lower()
        if target.tags.has(flag, category="flag"):
            target.tags.remove(flag, category="flag")
            self.msg(f"Flag {flag} removed from {target.key}.")
        else:
            self.msg("Flag not set.")

