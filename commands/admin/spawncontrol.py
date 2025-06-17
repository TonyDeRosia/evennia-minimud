from evennia import CmdSet
from evennia.scripts.models import ScriptDB
from ..command import Command


class CmdSpawnReload(Command):
    """Reload all spawn entries from NPC prototypes."""

    key = "@spawnreload"
    locks = "cmd:perm(Admin)"
    help_category = "Admin"

    def func(self):
        script = ScriptDB.objects.filter(db_key="spawn_manager").first()
        if not script or not hasattr(script, "reload_spawns"):
            self.msg("Spawn manager not found.")
            return
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
        if not script or not hasattr(script, "force_respawn"):
            self.msg("Spawn manager not found.")
            return
        script.force_respawn(room_vnum)
        self.msg(f"Respawn check run for room {room_vnum}.")


class CmdShowSpawns(Command):
    """Display spawn entries for a room."""

    key = "@showspawns"
    locks = "cmd:perm(Builder)"
    help_category = "Building"

    def func(self):
        arg = self.args.strip()
        script = ScriptDB.objects.filter(db_key="spawn_manager").first()
        if not script:
            self.msg("Spawn manager not found.")
            return

        if arg:
            if not arg.isdigit():
                self.msg("Usage: @showspawns [room_vnum]")
                return
            target_vnum = int(arg)
        else:
            target_vnum = getattr(self.caller.location.db, "room_id", None)
            if target_vnum is None:
                self.msg("Current room has no VNUM.")
                return

        lines = []
        for entry in script.db.entries:
            if script._normalize_room_id(entry.get("room")) != target_vnum:
                continue

            obj = script._get_room(entry)
            live = script._live_count(entry.get("prototype"), obj) if obj else 0
            lines.append(
                f"{entry.get('prototype')} (max {entry.get('max_count')}, respawn {entry.get('respawn_rate')}s, live {live})"
            )

        if lines:
            self.msg("Spawn entries:\n" + "\n".join(lines))
        else:
            self.msg("No spawn entries found.")


class SpawnControlCmdSet(CmdSet):
    key = "SpawnControlCmdSet"

    def at_cmdset_creation(self):
        super().at_cmdset_creation()
        self.add(CmdSpawnReload)
        self.add(CmdForceRespawn)
        self.add(CmdShowSpawns)
