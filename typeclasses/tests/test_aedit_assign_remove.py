from unittest.mock import MagicMock, patch
from django.test import override_settings
from evennia.utils.test_resources import EvenniaTest
from commands.admin import BuilderCmdSet
from world.areas import Area
from commands import aedit


@override_settings(DEFAULT_HOME=None)
class TestAEditAssignRemove(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.char1.msg = MagicMock()
        self.char1.cmdset.add_default(BuilderCmdSet)

    @patch("commands.aedit.update_area")
    @patch("commands.aedit.save_prototype")
    @patch("commands.aedit.load_prototype")
    @patch("commands.aedit.parse_area_identifier")
    def test_assign_room(self, mock_parse, mock_load_proto, mock_save, mock_update):
        area = Area(key="zone", start=5, end=10, rooms=[6, 7])
        mock_parse.return_value = area
        mock_load_proto.return_value = {"vnum": 12}
        cmd = aedit.CmdAEdit()
        cmd.caller = self.char1
        cmd.session = self.char1.sessions.get()
        cmd.args = "assign zone 12"
        cmd.func()
        assert 12 in area.rooms
        assert area.end == 12
        proto = mock_save.call_args[0][1]
        assert proto["area"] == "zone"
        mock_update.assert_called_with(0, area)

    @patch("commands.aedit.update_area")
    @patch("commands.aedit.parse_area_identifier")
    def test_remove_room(self, mock_parse, mock_update):
        area = Area(key="zone", start=1, end=5, rooms=[1, 2, 3])
        mock_parse.return_value = area
        cmd = aedit.CmdAEdit()
        cmd.caller = self.char1
        cmd.session = self.char1.sessions.get()
        cmd.args = "remove zone 2"
        cmd.func()
        assert 2 not in area.rooms
        mock_update.assert_called_with(0, area)
