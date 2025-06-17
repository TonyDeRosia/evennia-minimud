from unittest.mock import patch, MagicMock
from django.test import override_settings
from evennia.utils.test_resources import EvenniaTest
from commands.admin import BuilderCmdSet
from typeclasses.rooms import Room
from world.areas import Area
from commands import aedit

@override_settings(DEFAULT_HOME=None)
class TestASaveCoordinates(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.char1.permissions.add("Builder")
        self.char1.cmdset.add_default(BuilderCmdSet)
        self.char1.msg = MagicMock()

    @patch("commands.aedit.update_area")
    @patch("commands.aedit.save_prototype")
    @patch("commands.aedit.proto_from_room")
    @patch("commands.aedit.ObjectDB.objects.filter")
    @patch("commands.aedit.get_areas")
    def test_coords_updated(self, mock_get_areas, mock_filter, mock_proto, mock_save, mock_update):
        room1 = self.room1
        room2 = self.room2
        room1.db.coord = (0, 0)
        room1.db.area = "zone"
        room1.db.room_id = 1
        room2.db.coord = (1, 0)
        room2.db.area = "zone"
        room2.db.room_id = 2
        room1.db.exits = {"south": room2}
        room2.db.exits = {"north": room1}

        area = Area(key="zone", start=1, end=2, rooms=[1, 2])
        mock_get_areas.return_value = [area]

        def _filter(**kwargs):
            val = kwargs.get("db_attributes__db_value")
            return [room1] if val == 1 else [room2]

        mock_filter.side_effect = _filter
        mock_proto.side_effect = lambda r: {}

        cmd = aedit.CmdASave()
        cmd.caller = self.char1
        cmd.session = self.char1.sessions.get()
        cmd.args = "changed"
        cmd.func()

        self.assertEqual(room2.db.coord, (0, -1))

