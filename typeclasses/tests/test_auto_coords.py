from unittest.mock import patch, MagicMock
from django.test import override_settings
from evennia.utils.test_resources import EvenniaTest
from commands.admin import BuilderCmdSet
from typeclasses.rooms import Room
from world.areas import Area
from evennia.utils import create


@override_settings(DEFAULT_HOME=None)
class TestAutoCoordinates(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.char1.permissions.add("Builder")
        self.char1.cmdset.add_default(BuilderCmdSet)
        self.char1.msg = MagicMock()

    @patch("commands.building.update_area")
    @patch("commands.building.find_area")
    @patch("commands.building.find_area_by_vnum")
    def test_dig_sets_coordinates(self, mock_find_by, mock_find, mock_update):
        area = Area(key="zone", start=200000, end=200100)
        mock_find_by.return_value = area
        mock_find.return_value = (0, area)
        self.char1.location.db.coord = (2, 2)
        self.char1.execute_cmd("@dig north 200001")
        new_room = self.char1.location.db.exits.get("north")
        assert new_room.db.coord == (2, 3)

    @patch("commands.building.ObjectDB.objects.filter")
    @patch("commands.building.update_area")
    @patch("commands.building.find_area")
    @patch("commands.building.find_area_by_vnum")
    def test_link_sets_coordinates(self, mock_find_by, mock_find, mock_update, mock_filter):
        area = Area(key="zone", start=200000, end=200100)
        mock_find_by.return_value = area
        mock_find.return_value = (0, area)
        start = self.char1.location
        start.db.coord = (0, 0)
        target = create.create_object(Room, key="target", location=None)
        target.set_area("zone", 200002)
        target.db.coord = None
        mock_filter.return_value = [target]
        self.char1.execute_cmd("@link east 200002")
        assert target.db.coord == (1, 0)
