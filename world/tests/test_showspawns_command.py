from unittest import TestCase, mock
from commands.admin.spawncontrol import CmdShowSpawns

class TestShowSpawns(TestCase):
    def test_entries_exist(self):
        cmd = CmdShowSpawns()
        cmd.caller = mock.Mock()
        cmd.caller.location = mock.Mock()
        cmd.caller.location.db.room_id = 1
        cmd.args = ""
        cmd.msg = mock.Mock()
        script = mock.MagicMock()
        script._get_room.return_value = cmd.caller.location
        script._live_count.return_value = 1
        cmd.caller.location.db.spawn_entries = [
            {"prototype": "goblin", "max_count": 2, "respawn_rate": 30, "active_mobs": [], "dead_mobs": []}
        ]
        with mock.patch("commands.admin.spawncontrol.ScriptDB") as mock_sdb:
            mock_sdb.objects.filter.return_value.first.return_value = script
            cmd.func()
        cmd.msg.assert_called_with("Spawn entries:\n" +
                                   "goblin (max 2, respawn 30s, live 1)")

    def test_no_entries(self):
        cmd = CmdShowSpawns()
        cmd.caller = mock.Mock()
        cmd.caller.location = mock.Mock()
        cmd.caller.location.db.room_id = 1
        cmd.args = ""
        cmd.msg = mock.Mock()
        script = mock.MagicMock()
        script._get_room.return_value = cmd.caller.location
        cmd.caller.location.db.spawn_entries = []
        with mock.patch("commands.admin.spawncontrol.ScriptDB") as mock_sdb:
            mock_sdb.objects.filter.return_value.first.return_value = script
            cmd.func()
        cmd.msg.assert_called_with("No spawn entries found.")
