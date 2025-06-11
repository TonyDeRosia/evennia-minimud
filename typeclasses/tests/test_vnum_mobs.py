from unittest.mock import MagicMock, patch
from tempfile import TemporaryDirectory
from pathlib import Path
from unittest import mock

from django.test import override_settings
from django.conf import settings
from evennia.utils.test_resources import EvenniaTest

from commands.admin import BuilderCmdSet
from commands import npc_builder
from utils.mob_proto import register_prototype, spawn_from_vnum, get_prototype
from utils import vnum_registry
from world.scripts.mob_db import get_mobdb
from typeclasses.npcs import BaseNPC


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

    def test_mspawn_prefixed_vnum(self):
        proto = {"key": "orc", "typeclass": "typeclasses.npcs.BaseNPC"}
        vnum = register_prototype(proto, vnum=5)
        with mock.patch(
            "utils.vnum_registry.validate_vnum",
            wraps=vnum_registry.validate_vnum,
        ) as mock_validate:
            self.char1.execute_cmd(f"@mspawn M{vnum}")
        mock_validate.assert_called_with(vnum, "npc")
        npc = [
            o
            for o in self.char1.location.contents
            if o.is_typeclass(BaseNPC, exact=False)
        ][0]
        self.assertEqual(npc.db.vnum, vnum)
        self.assertTrue(npc.tags.has(f"M{vnum}", category="vnum"))

    def test_mspawn_key_resolves_vnum(self):
        proto = {"key": "orc", "typeclass": "typeclasses.npcs.BaseNPC"}
        vnum = register_prototype(proto, vnum=7)
        with mock.patch(
            "utils.mob_proto.spawn_from_vnum", wraps=spawn_from_vnum
        ) as mock_spawn:
            self.char1.execute_cmd("@mspawn orc")
        mock_spawn.assert_called_with(vnum, location=self.char1.location)

    def test_builder_sets_vnum_on_npc_and_proto(self):
        """Creating an NPC with a VNUM should store it on the NPC and prototype."""
        from world import prototypes

        self.char1.ndb.buildnpc = {
            "key": "ogre",
            "npc_type": "base",
            "vnum": 12,
            "creature_type": "humanoid",
        }
        npc_builder._create_npc(self.char1, "", register=True)

        npc = [o for o in self.char1.location.contents if o.key == "ogre"][0]
        self.assertEqual(npc.db.vnum, 12)
        self.assertTrue(npc.tags.has("M12", category="vnum"))

        registry = prototypes.get_npc_prototypes()
        self.assertEqual(registry["ogre"]["vnum"], 12)

    def test_builder_registers_vnum_for_mspawn(self):
        """NPCs built with a VNUM should be spawnable via @mspawn M<number>."""
        vnum = 22
        self.char1.ndb.buildnpc = {
            "key": "bugbear",
            "npc_type": "base",
            "vnum": vnum,
            "creature_type": "humanoid",
        }
        npc_builder._create_npc(self.char1, "", register=True)

        mob_db = get_mobdb()
        self.assertIsNotNone(mob_db.get_proto(vnum))

        self.char1.msg.reset_mock()
        self.char1.execute_cmd(f"@mspawn M{vnum}")
        msg = self.char1.msg.call_args[0][0]
        self.assertIn("Spawned", msg)
        npcs = [
            o
            for o in self.char1.location.contents
            if o.is_typeclass(BaseNPC, exact=False)
        ]
        self.assertGreaterEqual(len(npcs), 2)
