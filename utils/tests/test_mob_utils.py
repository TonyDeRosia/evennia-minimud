from unittest.mock import patch

from evennia.utils.test_resources import EvenniaTest
from django.test import override_settings

from utils.mob_utils import (
    assign_next_vnum,
    add_to_mlist,
    auto_calc,
    auto_calc_secondary,
    make_corpse,
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

    def test_make_corpse_adds_decay_script(self):
        from evennia.utils import create
        from typeclasses.characters import NPC

        npc = create.create_object(NPC, key="mob", location=self.room1)
        npc.db.corpse_decay_time = 1

        corpse = make_corpse(npc)
        script = corpse.scripts.get("decay")[0]
        self.assertEqual(script.interval, 60)

    def test_make_corpse_no_loot_empty(self):
        from evennia.utils import create
        from typeclasses.characters import NPC
        from typeclasses.objects import Object

        npc = create.create_object(NPC, key="mob", location=self.room1)
        npc.db.actflags = ["noloot"]

        inv_item = create.create_object(Object, key="inv", location=npc)
        eq_item = create.create_object(Object, key="sword", location=npc)
        npc.db.equipment = {"mainhand": eq_item}

        corpse = make_corpse(npc)
        self.assertFalse(corpse.contents)
        self.assertEqual(inv_item.location, npc)
        self.assertEqual(eq_item.location, npc)
