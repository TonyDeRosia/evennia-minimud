from evennia import CmdSet
from ..command import Command
from evennia.scripts.models import ScriptDB

class CmdResetWorld(Command):
    """Trigger respawn checks for all areas without despawning existing mobs."""

    key = "@resetworld"
    aliases = ["@refreshworld", "@respawnworld"]
    locks = "cmd:perm(Builder)"
    help_category = "Admin"

    def func(self):
        script = ScriptDB.objects.filter(db_key="spawn_manager").first()
        if not script:
            self.msg("Spawn manager not found.")
            return
        areas = {entry.get("area") for entry in script.db.entries}
        if not areas:
            self.msg("No areas found to reset.")
            return
        for key in areas:
            for entry in script.db.entries:
                if entry.get("area") == key:
                    rid = entry.get("room")
                    if isinstance(rid, str) and rid.isdigit():
                        rid = int(rid)
                    script.force_respawn(rid)
        self.msg(f"World reset complete. [{len(areas)}] areas repopulated.")

class ResetWorldCmdSet(CmdSet):
    key = "ResetWorldCmdSet"

    def at_cmdset_creation(self):
        super().at_cmdset_creation()
        self.add(CmdResetWorld)
