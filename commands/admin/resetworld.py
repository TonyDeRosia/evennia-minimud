from evennia import CmdSet
from ..command import Command
from world import spawn_manager

class CmdResetWorld(Command):
    """Reset all areas by despawning and respawning spawns."""

    key = "@resetworld"
    aliases = ["@refreshworld"]
    locks = "cmd:perm(Builder)"
    help_category = "Admin"

    def func(self):
        area_keys = spawn_manager.SpawnManager.get_area_keys()
        if not area_keys:
            self.msg("No areas found to reset.")
            return
        for key in area_keys:
            spawn_manager.SpawnManager.reset_area(key)
        self.msg(f"World reset complete. [{len(area_keys)}] areas repopulated.")

class ResetWorldCmdSet(CmdSet):
    key = "ResetWorldCmdSet"

    def at_cmdset_creation(self):
        super().at_cmdset_creation()
        self.add(CmdResetWorld)
