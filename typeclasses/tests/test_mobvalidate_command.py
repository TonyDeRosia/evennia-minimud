from unittest.mock import MagicMock
from tempfile import TemporaryDirectory
from pathlib import Path
from unittest import mock

from django.test import override_settings
from django.conf import settings
from evennia.utils.test_resources import EvenniaTest

from commands.admin import BuilderCmdSet
from world import prototypes


@override_settings(DEFAULT_HOME=None)
class TestMobValidateCommand(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.char1.msg = MagicMock()
        self.char1.cmdset.add_default(BuilderCmdSet)
        self.tmp = TemporaryDirectory()
        patcher = mock.patch.object(
            settings,
            "PROTOTYPE_NPC_FILE",
            Path(self.tmp.name) / "npcs.json",
        )
        self.addCleanup(self.tmp.cleanup)
        self.addCleanup(patcher.stop)
        patcher.start()

    def test_mobvalidate_reports_warnings(self):
        prototypes.register_npc_prototype(
            "goblin",
            {"key": "goblin", "hp": 0, "actflags": ["aggressive", "wimpy"]},
        )
        self.char1.execute_cmd("@mobvalidate goblin")
        out = self.char1.msg.call_args[0][0]
        assert "Warnings" in out
        assert "HP is set to zero" in out
        assert "aggressive" in out.lower()

