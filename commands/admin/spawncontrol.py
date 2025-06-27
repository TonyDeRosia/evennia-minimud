from evennia import CmdSet
from utils.script_utils import get_spawn_manager
from ..command import Command


class CmdSpawnReload(Command):
    """Reload all spawn entries from room prototypes."""

    key = "@spawnreload"
    locks = "cmd:perm(Admin)"
    help_category = "Admin"

    def func(self):
        script = get_spawn_manager()
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
        script = get_spawn_manager()
        if not script or not hasattr(script, "force_respawn"):
            self.msg("Spawn manager not found.")
            return

        if arg:
            if not arg.isdigit():
                self.msg("Usage: @forcerespawn <room_vnum>")
                return
            room_vnum = int(arg)
        else:
            room_vnum = getattr(self.caller.location.db, "room_id", None)
            if room_vnum is None:
                self.msg("Current room has no VNUM.")
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
        script = get_spawn_manager()
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

        room = script._get_room({"room": target_vnum, "room_id": target_vnum})
        if not room:
            self.msg("Room not found.")
            return

        lines = []
        for entry in room.db.spawn_entries or []:
            proto = entry.get("prototype")
            live = script._live_count(proto, room)
            lines.append(
                f"{proto} (max {entry.get('max_count')}, respawn {entry.get('respawn_rate')}s, live {live})"
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
