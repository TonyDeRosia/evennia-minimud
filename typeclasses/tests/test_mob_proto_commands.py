from unittest.mock import MagicMock
from tempfile import TemporaryDirectory
from pathlib import Path
from evennia.utils.test_resources import EvenniaTest
from django.test import override_settings
from django.conf import settings
from unittest import mock

from commands.admin import BuilderCmdSet
from world import prototypes
from utils.mob_proto import register_prototype, spawn_from_vnum, get_prototype
from world.scripts.mob_db import get_mobdb


@override_settings(DEFAULT_HOME=None)
class TestMobPrototypeCommands(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.char1.msg = MagicMock()
        self.char1.cmdset.add_default(BuilderCmdSet)
        self.tmp = TemporaryDirectory()
        patcher1 = mock.patch.object(
            settings,
            "PROTOTYPE_NPC_FILE",
            Path(self.tmp.name) / "npcs.json",
        )
        patcher2 = mock.patch.object(
            settings,
            "VNUM_REGISTRY_FILE",
            Path(self.tmp.name) / "vnums.json",
        )
        self.addCleanup(self.tmp.cleanup)
        self.addCleanup(patcher1.stop)
        self.addCleanup(patcher2.stop)
        patcher1.start()
        patcher2.start()

    def test_mcreate_and_mset(self):
        self.char1.execute_cmd("@mcreate goblin")
        reg = prototypes.get_npc_prototypes()
        self.assertIn("goblin", reg)
        self.char1.execute_cmd('@mset goblin desc "A small goblin"')
        reg = prototypes.get_npc_prototypes()
        self.assertEqual(reg["goblin"]["desc"], "A small goblin")

    def test_mcreate_copy(self):
        prototypes.register_npc_prototype("base", {"key": "base", "desc": "base"})
        self.char1.execute_cmd("@mcreate gob base")
        reg = prototypes.get_npc_prototypes()
        self.assertEqual(reg["gob"]["desc"], "base")

    def test_mstat_and_mlist_range(self):
        prototypes.register_npc_prototype("aone", {"key": "aone"})
        prototypes.register_npc_prototype("btwo", {"key": "btwo"})
        prototypes.register_npc_prototype("cthree", {"key": "cthree"})
        self.char1.execute_cmd("@mstat aone")
        out = self.char1.msg.call_args[0][0]
        self.assertIn("aone", out)
        self.char1.msg.reset_mock()
        self.char1.execute_cmd("@mlist a-c")
        out = self.char1.msg.call_args[0][0]
        self.assertIn("aone", out)
        self.assertIn("btwo", out)
        self.assertNotIn("cthree", out)

    def test_shop_and_repair_commands(self):
        self.char1.execute_cmd("@mcreate shopkeep")
        self.char1.execute_cmd("@makeshop shopkeep")
        reg = prototypes.get_npc_prototypes()
        self.assertIn("shop", reg["shopkeep"])
        self.char1.execute_cmd("@shopset shopkeep buy 150")
        self.char1.execute_cmd("@shopset shopkeep sell 50")
        self.char1.execute_cmd("@shopset shopkeep hours 9-17")
        self.char1.execute_cmd("@shopset shopkeep types weapon,armor")
        reg = prototypes.get_npc_prototypes()
        shop = reg["shopkeep"]["shop"]
        self.assertEqual(shop["buy_percent"], 150)
        self.assertEqual(shop["sell_percent"], 50)
        self.assertEqual(shop["hours"], "9-17")
        self.assertEqual(shop["item_types"], ["weapon", "armor"])
        self.char1.execute_cmd("@shopstat shopkeep")
        out = self.char1.msg.call_args[0][0]
        self.assertIn("Buy Percent", out)
        self.char1.msg.reset_mock()

        self.char1.execute_cmd("@makerepair shopkeep")
        self.char1.execute_cmd("@repairset shopkeep cost 200")
        self.char1.execute_cmd("@repairset shopkeep hours 10-20")
        self.char1.execute_cmd("@repairset shopkeep types weapon")
        reg = prototypes.get_npc_prototypes()
        repair = reg["shopkeep"]["repair"]
        self.assertEqual(repair["cost_percent"], 200)
        self.assertEqual(repair["hours"], "10-20")
        self.assertEqual(repair["item_types"], ["weapon"])
        self.char1.execute_cmd("@repairstat shopkeep")
        out = self.char1.msg.call_args[0][0]
        self.assertIn("Cost Percent", out)

    def test_delete_checks_live_npcs(self):
        get_mobdb()
        vnum = register_prototype(
            {"key": "orc", "typeclass": "typeclasses.npcs.BaseNPC"}, vnum=1
        )
        npc = spawn_from_vnum(vnum, location=self.char1.location)
        self.char1.execute_cmd(f"@mobproto delete {vnum}")
        out = self.char1.msg.call_args[0][0]
        self.assertIn("live NPCs", out)
        npc.delete()
        self.char1.msg.reset_mock()
        self.char1.execute_cmd(f"@mobproto delete {vnum}")
        out = self.char1.msg.call_args[0][0]
        self.assertIn("deleted", out)
        self.assertIsNone(get_prototype(vnum))

    def test_spawn_reports_missing_fields(self):
        vnum = register_prototype({"desc": "bad"}, vnum=50)
        self.char1.msg.reset_mock()
        self.char1.execute_cmd(f"@mobproto spawn {vnum}")
        out = self.char1.msg.call_args[0][0]
        assert "missing required field" in out.lower()

    def test_invalid_typeclass(self):
        with self.assertRaises(ValueError):
            register_prototype({"key": "bad", "typeclass": "typeclasses.objects.ObjectParent"}, vnum=51)


