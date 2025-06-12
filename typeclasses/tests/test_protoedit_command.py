from unittest.mock import MagicMock
from tempfile import TemporaryDirectory
from pathlib import Path
from unittest import mock

from django.test import override_settings
from django.conf import settings
from evennia.utils.test_resources import EvenniaTest

from commands.admin import BuilderCmdSet
from utils.mob_proto import register_prototype, get_prototype


@override_settings(DEFAULT_HOME=None)
class TestProtoEdit(EvenniaTest):
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

    def test_protoedit_sets_field(self):
        register_prototype({"key": "orc"}, vnum=5)
        self.char1.execute_cmd("@protoedit 5 level 3")
        self.assertEqual(get_prototype(5)["level"], 3)

    def test_protoedit_shows_summary(self):
        register_prototype({"key": "orc", "level": 2}, vnum=7)
        self.char1.msg.reset_mock()
        self.char1.execute_cmd("@protoedit 7")
        out = self.char1.msg.call_args[0][0]
        self.assertIn("orc", out)
        self.assertIn("2", out)
