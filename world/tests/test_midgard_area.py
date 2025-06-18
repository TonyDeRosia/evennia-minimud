from evennia.utils.test_resources import EvenniaTest
from world.areas import find_area_by_vnum
from utils.prototype_manager import load_prototype


class TestMidgardArea(EvenniaTest):
    def test_lookup_midgard(self):
        area = find_area_by_vnum(200050)
        assert area and area.key == "midgard"

    def test_load_room_prototype(self):
        proto = load_prototype("room", 200070)
        assert proto and proto.get("area") == "midgard"
