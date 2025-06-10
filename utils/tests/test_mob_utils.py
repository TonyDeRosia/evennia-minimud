from unittest.mock import patch

from evennia.utils.test_resources import EvenniaTest
from django.test import override_settings

from utils.mob_utils import (
    assign_next_vnum,
    add_to_mlist,
    auto_calc,
    auto_calc_secondary,
)
from world.scripts.mob_db import get_mobdb
from world.system import stat_manager


@override_settings(DEFAULT_HOME=None)
class TestMobUtils(EvenniaTest):
    def test_assign_next_vnum_delegates(self):
        with patch("utils.vnum_registry.get_next_vnum", return_value=42) as mock:
            val = assign_next_vnum("npc")
            self.assertEqual(val, 42)
            mock.assert_called_with("npc")

    def test_add_to_mlist_stores_entry(self):
        proto = {"key": "orc"}
        add_to_mlist(5, proto)
        mob_db = get_mobdb()
        self.assertEqual(mob_db.get_proto(5)["key"], "orc")

    def test_auto_calc_secondary(self):
        prims = {"STR": 5, "CON": 5}
        derived = auto_calc(prims)
        expected_hp = int(round(
            prims["CON"] * stat_manager.STAT_SCALING["HP"]["CON"]
            + prims["STR"] * stat_manager.STAT_SCALING["HP"]["STR"]
        ))
        self.assertEqual(derived["HP"], expected_hp)
        sec = auto_calc_secondary(prims)
        self.assertNotIn("HP", sec)
