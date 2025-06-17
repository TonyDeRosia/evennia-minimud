from evennia import CmdSet
from ..command import Command
from evennia.scripts.models import ScriptDB


class CmdSpawnReload(Command):
    """Reload all spawn entries from NPC prototypes."""

    key = "@spawnreload"
    locks = "cmd:perm(Admin)"
    help_category = "Admin"

    def func(self):
        script = ScriptDB.objects.filter(db_key="spawn_manager").first()
        if script:
            script.reload_spawns()
        self.msg("Spawn entries reloaded from prototypes.")


class CmdForceRespawn(Command):
    """Run spawn checks immediately for a room."""

    key = "@forcerespawn"
    locks = "cmd:perm(Admin)"
    help_category = "Admin"

    def func(self):
        arg = self.args.strip()
        if not arg.isdigit():
            self.msg("Usage: @forcerespawn <room_vnum>")
            return
        room_vnum = int(arg)
        script = ScriptDB.objects.filter(db_key="spawn_manager").first()
        if script:
            script.force_respawn(room_vnum)
        self.msg(f"Respawn check run for room {room_vnum}.")


class SpawnControlCmdSet(CmdSet):
    key = "SpawnControlCmdSet"

    def at_cmdset_creation(self):
        super().at_cmdset_creation()
        self.add(CmdSpawnReload)
        self.add(CmdForceRespawn)
