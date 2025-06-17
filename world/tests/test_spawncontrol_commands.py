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
