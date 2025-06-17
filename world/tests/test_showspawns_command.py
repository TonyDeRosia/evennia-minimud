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
        script.db.entries = [{"room": "#1", "prototype": "goblin", "max_count": 2, "respawn_rate": 30}]
        script._get_room.return_value = cmd.caller.location
        script._live_count.return_value = 1
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
        script.db.entries = []
        with mock.patch("commands.admin.spawncontrol.ScriptDB") as mock_sdb:
            mock_sdb.objects.filter.return_value.first.return_value = script
            cmd.func()
        cmd.msg.assert_called_with("No spawn entries found.")
