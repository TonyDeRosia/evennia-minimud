from unittest import mock
from evennia.utils.test_resources import EvenniaTest
from world.areas import Area, find_area_by_vnum

class TestFindAreaByVnum(EvenniaTest):
    def test_lookup(self):
        areas = [Area(key="zone", start=1, end=5), Area(key="dungeon", start=10, end=20)]
        with mock.patch("world.areas.get_areas", return_value=areas):
            assert find_area_by_vnum(3).key == "zone"
            assert find_area_by_vnum(15).key == "dungeon"
            assert find_area_by_vnum(30) is None
