from evennia import CmdSet, search_object
from django.conf import settings

from .command import Command


class CmdRecall(Command):
    """Teleport to your saved recall location."""

    key = "recall"
    help_category = "General"

    def func(self):
        caller = self.caller
        dest = caller.db.recall_location
        if not dest:
            default_ref = getattr(settings, "DEFAULT_RECALL_ROOM", "#2")
            dest_list = search_object(default_ref)
            dest = dest_list[0] if dest_list else None
            if not dest:
                caller.msg("You have not set a recall location.")
                return
        if caller.location and caller.location.tags.has("no_recall", category="room_flag"):
            caller.msg("You cannot recall from here.")
            return
        if not dest.is_typeclass("typeclasses.rooms.Room", exact=False):
            caller.msg("Your recall location is invalid.")
            return
        caller.move_to(dest, quiet=True, move_type="teleport")
        caller.msg(f"You recall to {dest.get_display_name(caller)}.")


class CmdSetRecall(Command):
    """Set your recall location to the current room."""

    key = "setrecall"
    help_category = "General"

    def func(self):
        caller = self.caller
        if not caller.has_account:
            caller.msg("Only players can set recall points.")
            return
        room = caller.location
        if not room or not room.tags.has("sanctuary", category="room_flag"):
            caller.msg("You may only set recall in a sanctuary.")
            return
        caller.db.recall_location = room
        caller.msg(f"Recall location set to {room.get_display_name(caller)}.")


class RecallCmdSet(CmdSet):
    key = "Recall CmdSet"

    def at_cmdset_creation(self):
        super().at_cmdset_creation()
        self.add(CmdRecall)
        self.add(CmdSetRecall)
