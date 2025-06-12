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
        with patch("utils.mob_proto.finalize_mob_prototype") as mock_final:
            with patch(
                "evennia.prototypes.spawner.spawn", return_value=[npc_mock]
            ) as mock_spawn:
                npc = spawn_from_vnum(vnum, location=self.char1.location)
        mock_spawn.assert_called()
        mock_final.assert_called_with(npc_mock, npc_mock)
        self.assertIs(npc, npc_mock)
        self.assertEqual(npc.location, self.char1.location)
        self.assertEqual(npc.db.vnum, vnum)
        self.assertEqual(npc.tags.get(category="vnum"), f"M{vnum}")
        mob_db = get_mobdb()
        self.assertEqual(mob_db.get_proto(vnum)["spawn_count"], 1)

    def test_spawn_sets_default_combat_stats(self):
        proto = {
            "key": "orc",
            "typeclass": "typeclasses.npcs.BaseNPC",
            "level": 2,
            "combat_class": "Warrior",
        }
        vnum = register_prototype(proto, vnum=3)
        npc = spawn_from_vnum(vnum, location=self.char1.location)
        stats = npc_builder.generate_base_stats("Warrior", 2)
        self.assertEqual(npc.db.hp, stats["hp"])
        self.assertEqual(npc.db.mp, stats["mp"])
        self.assertEqual(npc.db.sp, stats["sp"])
        self.assertEqual(npc.db.armor, stats["armor"])
        self.assertEqual(npc.db.initiative, stats["initiative"])
        self.assertEqual(npc.db.charclass, "Warrior")

    def test_spawn_applies_role_mixins(self):
        proto = {
            "key": "clerk",
            "typeclass": "typeclasses.npcs.BaseNPC",
            "metadata": {"roles": ["merchant", "banker"]},
        }
        vnum = register_prototype(proto, vnum=4)
        npc = spawn_from_vnum(vnum, location=self.char1.location)
        self.assertTrue(callable(getattr(npc, "sell", None)))
        self.assertTrue(callable(getattr(npc, "deposit", None)))

    def test_command_set_flow(self):
        self.char1.execute_cmd("@mobproto create 1 gob")
        self.assertIn("key", get_prototype(1))

        self.char1.execute_cmd('@mobproto set 1 desc "Green goblin"')
        self.assertEqual(get_prototype(1)["desc"], "Green goblin")

        self.char1.execute_cmd("@mobproto create 2 orc")

        with patch("commands.cmdmobbuilder.EvMenu") as mock_menu:
            self.char1.execute_cmd("@mobproto edit 1")
        mock_menu.assert_called_with(
            self.char1,
            "commands.npc_builder",
            startnode="menunode_desc",
            cmd_on_exit=npc_builder._on_menu_exit,
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

    def test_saved_vnum_message(self):
        """Building with Yes & Save Prototype should show spawn instructions."""
        vnum = 30
        self.char1.ndb.buildnpc = {
            "key": "kobold",
            "npc_type": "base",
            "vnum": vnum,
            "creature_type": "humanoid",
            "combat_class": "Warrior",
            "level": 1,
        }
        npc_builder._create_npc(self.char1, "", register=True)

        out = "".join(call.args[0] for call in self.char1.msg.call_args_list)
        self.assertIn(f"Mob saved and registered as VNUM {vnum}", out)
        self.assertIn(f"@mspawn M{vnum}", out)

    def test_mspawn_not_finalized_message(self):
        """Valid VNUMs without prototypes should show a helpful error."""
        with patch("utils.mob_proto.spawn_from_vnum") as mock_spawn:
            self.char1.execute_cmd("@mspawn 42")
            mock_spawn.assert_not_called()
        out = self.char1.msg.call_args[0][0]
        self.assertIn("not finalized", out)
        self.assertIn("editnpc 42", out)
