from unittest.mock import MagicMock, patch
from tempfile import TemporaryDirectory
from pathlib import Path
from unittest import mock

from django.test import override_settings
from django.conf import settings
from evennia.utils.test_resources import EvenniaTest

from commands.admin import BuilderCmdSet
from utils.mob_proto import register_prototype, spawn_from_vnum, get_prototype
from world.scripts.mob_db import get_mobdb


@override_settings(DEFAULT_HOME=None)
class TestVnumMobs(EvenniaTest):
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

    def test_register_and_spawn_vnum(self):
        proto = {"key": "goblin", "typeclass": "typeclasses.npcs.BaseNPC"}
        vnum = register_prototype(proto, vnum=1)
        npc_mock = MagicMock()
        with patch(
            "evennia.prototypes.spawner.spawn", return_value=[npc_mock]
        ) as mock_spawn:
            npc = spawn_from_vnum(vnum, location=self.char1.location)
        mock_spawn.assert_called()
        self.assertIs(npc, npc_mock)
        self.assertEqual(npc.location, self.char1.location)
        self.assertEqual(npc.db.vnum, vnum)
        self.assertEqual(npc.tags.get(category="vnum"), f"M{vnum}")
        mob_db = get_mobdb()
        self.assertEqual(mob_db.get_proto(vnum)["spawn_count"], 1)

    def test_command_set_flow(self):
        self.char1.execute_cmd("@mobproto create 1 gob")
        self.assertIn("key", get_prototype(1))

        self.char1.execute_cmd('@mobproto set 1 desc "Green goblin"')
        self.assertEqual(get_prototype(1)["desc"], "Green goblin")

        self.char1.execute_cmd("@mobproto create 2 orc")

        with patch("commands.cmdmobbuilder.EvMenu") as mock_menu:
            self.char1.execute_cmd("@mobproto edit 1")
        mock_menu.assert_called_with(
            self.char1, "commands.npc_builder", startnode="menunode_desc"
        )
        self.assertEqual(self.char1.ndb.mob_vnum, 1)
        self.assertEqual(self.char1.ndb.buildnpc["key"], "gob")

        self.char1.msg.reset_mock()
        self.char1.execute_cmd("@mobproto list")
        list_out = self.char1.msg.call_args[0][0]
        self.assertIn("1", list_out)
        self.assertIn("2", list_out)
        self.assertIn("gob", list_out)
        self.assertIn("orc", list_out)

        self.char1.msg.reset_mock()
        self.char1.execute_cmd("@mobproto diff 1 2")
        diff_out = self.char1.msg.call_args[0][0]
        self.assertIn("desc", diff_out)

        self.char1.msg.reset_mock()
        self.char1.execute_cmd("@mobproto delete 1")
        self.assertIsNone(get_prototype(1))
        del_msg = self.char1.msg.call_args[0][0]
        self.assertIn("deleted", del_msg.lower())
