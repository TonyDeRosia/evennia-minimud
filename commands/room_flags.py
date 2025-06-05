from evennia import CmdSet
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


class CmdRFlags(Command):
    """List flags set on the current room."""

    key = "rflags"
    help_category = "Building"

    def func(self):
        room = self.caller.location
        if not room:
            self.msg("You have no location.")
            return
        flags = room.tags.get(category="room_flag", return_list=True) or []
        if not flags:
            self.msg("This room has no flags.")
        else:
            self.msg("Room flags: " + ", ".join(sorted(flags)))


class CmdRFlag(Command):
    """Add or remove room flags."""

    key = "rflag"
    locks = "cmd:perm(Builder)"
    help_category = "Building"

    def func(self):
        if not self.args:
            self.msg("Usage: rflag <add/remove/list> [flag]")
            return
        room = self.caller.location
        if not room:
            self.msg("You have no location.")
            return
        parts = self.args.split(None, 1)
        action = parts[0].lower()
        if action == "list":
            self.msg("Valid flags: " + ", ".join(VALID_ROOM_FLAGS))
            return
        if len(parts) < 2:
            self.msg("Usage: rflag <add/remove/list> <flag>")
            return
        flag = parts[1].lower()
        if flag not in VALID_ROOM_FLAGS:
            self.msg("Unknown flag.")
            return
        if action == "add":
            if room.tags.has(flag, category="room_flag"):
                self.msg("Flag already set.")
            else:
                room.tags.add(flag, category="room_flag")
                self.msg(f"Added {flag} flag.")
        elif action == "remove":
            if room.tags.has(flag, category="room_flag"):
                room.tags.remove(flag, category="room_flag")
                self.msg(f"Removed {flag} flag.")
            else:
                self.msg("Flag not set.")
        else:
            self.msg("Usage: rflag <add/remove/list> <flag>")


class RoomFlagCmdSet(CmdSet):
    key = "Room Flag CmdSet"

    def at_cmdset_creation(self):
        super().at_cmdset_creation()
        self.add(CmdRFlags)
        self.add(CmdRFlag)
