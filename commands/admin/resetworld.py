from evennia import CmdSet

from utils.script_utils import get_respawn_manager, respawn_area

from ..command import Command


class CmdResetWorld(Command):
    """Trigger respawn checks for all areas without despawning existing mobs."""

    key = "@resetworld"
    aliases = ["@refreshworld", "@respawnworld"]
    locks = "cmd:perm(Builder)"
    help_category = "Admin"

    def func(self):
        script = get_respawn_manager()
        if not script:
            self.msg("Spawn manager not found.")
            return
        areas = {entry.get("area") for entry in script.db.entries}
        if not areas:
            self.msg("No areas found to reset.")
            return
        for key in areas:
            respawn_area(key)
        self.msg(f"World reset complete. [{len(areas)}] areas repopulated.")


class ResetWorldCmdSet(CmdSet):
    key = "ResetWorldCmdSet"

    def at_cmdset_creation(self):
        super().at_cmdset_creation()
        self.add(CmdResetWorld)
