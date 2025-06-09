from unittest.mock import MagicMock
from tempfile import TemporaryDirectory
from pathlib import Path
from evennia.utils.test_resources import EvenniaTest
from django.test import override_settings
from unittest import mock

from commands.admin import BuilderCmdSet
from world import prototypes


@override_settings(DEFAULT_HOME=None)
class TestMobPrototypeCommands(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.char1.msg = MagicMock()
        self.char1.cmdset.add_default(BuilderCmdSet)
        self.tmp = TemporaryDirectory()
        patcher = mock.patch.object(
            prototypes,
            "_NPC_PROTO_FILE",
            Path(self.tmp.name) / "npcs.json",
        )
        self.addCleanup(self.tmp.cleanup)
        self.addCleanup(patcher.stop)
        patcher.start()

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

