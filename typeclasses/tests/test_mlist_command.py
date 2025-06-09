from unittest.mock import MagicMock
from tempfile import TemporaryDirectory
from pathlib import Path
from unittest import mock

from django.test import override_settings
from django.conf import settings
from evennia.utils.test_resources import EvenniaTest

from commands.admin import BuilderCmdSet
from world import prototypes, area_npcs


@override_settings(DEFAULT_HOME=None)
class TestMListCommand(EvenniaTest):
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

    def test_mlist_range(self):
        prototypes.register_npc_prototype("alpha", {"key": "alpha"})
        prototypes.register_npc_prototype("bravo", {"key": "bravo"})
        prototypes.register_npc_prototype("charlie", {"key": "charlie"})
        self.char1.execute_cmd("@mlist a-b")
        out = self.char1.msg.call_args[0][0]
        assert "alpha" in out
        assert "bravo" in out
        assert "charlie" not in out
