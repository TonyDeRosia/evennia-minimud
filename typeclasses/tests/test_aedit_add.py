from unittest.mock import MagicMock, patch
from django.test import override_settings
from evennia.utils.test_resources import EvenniaTest
from commands.admin import BuilderCmdSet
from world.areas import Area
from commands import aedit

@override_settings(DEFAULT_HOME=None)
class TestAEditAdd(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.char1.msg = MagicMock()
        self.char1.cmdset.add_default(BuilderCmdSet)

    @patch("commands.aedit.update_area")
    @patch("commands.aedit.save_prototype")
    @patch("commands.aedit.load_prototype")
    @patch("commands.aedit.parse_area_identifier")
    def test_add_room(self, mock_parse, mock_load_proto, mock_save, mock_update):
        area = Area(key="zone", start=1, end=5)
        mock_parse.return_value = area
        mock_load_proto.return_value = {"vnum": 3}
        cmd = aedit.CmdAEdit()
        cmd.caller = self.char1
        cmd.session = self.char1.sessions.get()
        cmd.args = "add zone 3"
        cmd.func()
        self.assertIn(3, area.rooms)
        proto = mock_save.call_args[0][1]
        self.assertEqual(proto["area"], "zone")
        mock_save.assert_called_with("room", proto, vnum=3)
        mock_update.assert_called_with(0, area)

    @patch("commands.aedit.update_area")
    @patch("commands.aedit.save_prototype")
    @patch("commands.aedit.load_prototype")
    @patch("commands.aedit.parse_area_identifier")
    def test_range_updates_end(self, mock_parse, mock_load_proto, mock_save, mock_update):
        area = Area(key="zone", start=5, end=10)
        mock_parse.return_value = area
        mock_load_proto.return_value = {"vnum": 12}
        cmd = aedit.CmdAEdit()
        cmd.caller = self.char1
        cmd.session = self.char1.sessions.get()
        cmd.args = "add zone 12"
        cmd.func()
        self.assertEqual(area.end, 12)
        mock_update.assert_called_with(0, area)

    @patch("commands.aedit.update_area")
    @patch("commands.aedit.save_prototype")
    @patch("commands.aedit.load_prototype")
    @patch("commands.aedit.parse_area_identifier")
    def test_range_updates_start(self, mock_parse, mock_load_proto, mock_save, mock_update):
        area = Area(key="zone", start=5, end=10)
        mock_parse.return_value = area
        mock_load_proto.return_value = {"vnum": 2}
        cmd = aedit.CmdAEdit()
        cmd.caller = self.char1
        cmd.session = self.char1.sessions.get()
        cmd.args = "add zone 2"
        cmd.func()
        self.assertEqual(area.start, 2)
        mock_update.assert_called_with(0, area)

