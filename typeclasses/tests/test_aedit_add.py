from unittest.mock import MagicMock, patch
from django.test import override_settings
from evennia.utils.test_resources import EvenniaTest
from commands.admin import BuilderCmdSet
from world.areas import Area

@override_settings(DEFAULT_HOME=None)
class TestAEditAdd(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.char1.msg = MagicMock()
        self.char1.cmdset.add_default(BuilderCmdSet)

    @patch("commands.aedit.update_area")
    @patch("commands.aedit.load_prototype")
    @patch("commands.aedit.find_area")
    def test_add_room(self, mock_find_area, mock_load_proto, mock_update):
        area = Area(key="zone", start=1, end=5)
        mock_find_area.return_value = (0, area)
        mock_load_proto.return_value = {"vnum": 3}
        self.char1.execute_cmd("aedit add zone 3")
        self.assertIn(3, area.rooms)
        mock_update.assert_called_with(0, area)

