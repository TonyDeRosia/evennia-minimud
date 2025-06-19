from unittest import TestCase, mock
from commands.admin.spawncontrol import CmdSpawnReload, CmdForceRespawn


class TestSpawnControlCommands(TestCase):
    def test_spawnreload_calls_script(self):
        cmd = CmdSpawnReload()
        cmd.caller = mock.Mock()
        cmd.args = ""
        cmd.msg = mock.Mock()
        with mock.patch("commands.admin.spawncontrol.ScriptDB") as mock_sdb:
            script = mock.Mock()
            mock_sdb.objects.filter.return_value.first.return_value = script
            cmd.func()
            script.reload_spawns.assert_called_once()
            cmd.msg.assert_called_with("Spawn entries reloaded from prototypes.")

    def test_force_respawn_calls_script(self):
        cmd = CmdForceRespawn()
        cmd.caller = mock.Mock()
        cmd.args = "5"
        cmd.msg = mock.Mock()
        with mock.patch("commands.admin.spawncontrol.ScriptDB") as mock_sdb:
            script = mock.Mock()
            mock_sdb.objects.filter.return_value.first.return_value = script
            cmd.func()
            script.force_respawn.assert_called_with(5)
            cmd.msg.assert_called_with("Respawn check run for room 5.")

    def test_force_respawn_defaults_to_current_room(self):
        cmd = CmdForceRespawn()
        cmd.caller = mock.Mock()
        cmd.caller.location = mock.Mock()
        cmd.caller.location.db.room_id = 3
        cmd.args = ""
        cmd.msg = mock.Mock()
        with mock.patch("commands.admin.spawncontrol.ScriptDB") as mock_sdb:
            script = mock.Mock()
            mock_sdb.objects.filter.return_value.first.return_value = script
            cmd.func()
            script.force_respawn.assert_called_with(3)
            cmd.msg.assert_called_with("Respawn check run for room 3.")

    def test_spawnreload_populates_entries_from_prototypes(self):
        cmd = CmdSpawnReload()
        cmd.caller = mock.Mock()
        cmd.args = ""
        cmd.msg = mock.Mock()

        class FakeScript:
            def __init__(self):
                self.db = mock.Mock(entries=[])

            def reload_spawns(self):
                from utils.prototype_manager import load_all_prototypes
                from world import prototypes
                from world.scripts.mob_db import get_mobdb

                self.db.entries = []
                room_protos = load_all_prototypes("room")
                npc_registry = prototypes.get_npc_prototypes()
                mob_db = get_mobdb()
                for proto in room_protos.values():
                    for entry in proto.get("spawns", []):
                        proto_key = entry.get("prototype")
                        if str(proto_key).isdigit():
                            proto_key = int(proto_key)
                            if not mob_db.get_proto(proto_key):
                                continue
                        elif proto_key not in npc_registry:
                            continue
                        rid = proto.get("vnum")
                        self.db.entries.append(
                            {
                                "area": (proto.get("area") or "").lower(),
                                "prototype": proto_key,
                                "room": rid,
                                "room_id": rid,
                                "max_count": int(entry.get("max_count", 1)),
                                "respawn_rate": int(entry.get("respawn_rate", 60)),
                                "last_spawn": 0.0,
                            }
                        )

        script = FakeScript()

        with mock.patch("commands.admin.spawncontrol.ScriptDB") as mock_sdb, \
             mock.patch("utils.prototype_manager.load_all_prototypes") as m_load, \
             mock.patch("world.prototypes.get_npc_prototypes", return_value={"orc": {}}), \
             mock.patch("world.scripts.mob_db.get_mobdb") as m_mobdb:
            m_load.return_value = {1: {"vnum": 1, "area": "test", "spawns": [{"prototype": "orc"}]}}
            m_mobdb.return_value = mock.Mock(get_proto=lambda v: {})
            mock_sdb.objects.filter.return_value.first.return_value = script
            cmd.func()

        self.assertEqual(len(script.db.entries), 1)
        self.assertEqual(script.db.entries[0]["prototype"], "orc")
        cmd.msg.assert_called_with("Spawn entries reloaded from prototypes.")

    def test_force_respawn_spawns_npc_in_room(self):
        cmd = CmdForceRespawn()
        cmd.caller = mock.Mock()
        cmd.args = "1"
        cmd.msg = mock.Mock()

        room = mock.Mock()

        class FakeScript:
            def __init__(self):
                self.db = mock.Mock(entries=[{"prototype": 5, "room": room, "room_id": 1}])

            def force_respawn(self, room_vnum):
                from utils.mob_proto import spawn_from_vnum

                for entry in list(self.db.entries):
                    if entry.get("room_id") == room_vnum:
                        spawn_from_vnum(entry.get("prototype"), location=entry.get("room"))

        script = FakeScript()

        with mock.patch("commands.admin.spawncontrol.ScriptDB") as mock_sdb, \
             mock.patch("utils.mob_proto.spawn_from_vnum") as m_spawn:
            mock_sdb.objects.filter.return_value.first.return_value = script
            cmd.func()
            m_spawn.assert_called_once_with(5, location=room)
            cmd.msg.assert_called_with("Respawn check run for room 1.")
