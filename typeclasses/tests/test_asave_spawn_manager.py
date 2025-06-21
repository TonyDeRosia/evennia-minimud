from unittest.mock import patch, MagicMock
from django.test import override_settings
from evennia.utils.test_resources import EvenniaTest
from commands.admin import BuilderCmdSet
from typeclasses.rooms import Room
from world.areas import Area
from commands import aedit


@override_settings(DEFAULT_HOME=None)
class TestASaveSpawnManager(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.char1.permissions.add("Builder")
        self.char1.cmdset.add_default(BuilderCmdSet)
        self.char1.msg = MagicMock()

    @patch("commands.aedit.update_area")
    @patch("commands.aedit.save_prototype")
    @patch("commands.aedit.proto_from_room")
    @patch("commands.aedit.get_spawn_manager")
    @patch("commands.aedit.ObjectDB.objects.filter")
    @patch("commands.aedit.get_areas")
    def test_spawn_manager_called(
        self,
        mock_get_areas,
        mock_obj_filter,
        mock_get_spawn_manager,
        mock_proto,
        mock_save,
        mock_update,
    ):
        room = self.room1
        room.db.area = "zone"
        room.db.room_id = 1
        area = Area(key="zone", start=1, end=1, rooms=[1])
        mock_get_areas.return_value = [area]
        mock_obj_filter.return_value = [room]
        proto = {"vnum": room.db.room_id}
        mock_proto.return_value = proto
        mock_script = MagicMock()
        mock_get_spawn_manager.return_value = mock_script

        cmd = aedit.CmdASave()
        cmd.caller = self.char1
        cmd.session = self.char1.sessions.get()
        cmd.args = "changed"
        cmd.func()

        mock_script.register_room_spawn.assert_called_with(proto)
        mock_script.force_respawn.assert_called_with(room.db.room_id)
