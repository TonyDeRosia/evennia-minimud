from unittest.mock import MagicMock
from tempfile import TemporaryDirectory
from pathlib import Path
from unittest import mock

from django.test import override_settings
from evennia.utils.test_resources import EvenniaTest

from commands.admin import BuilderCmdSet
from world import prototypes


@override_settings(DEFAULT_HOME=None)
class TestMSetCommand(EvenniaTest):
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

    def test_mset_edits_field(self):
        prototypes.register_npc_prototype("orc", {"key": "orc"})
        self.char1.execute_cmd('@mset orc desc "Fierce orc"')
        reg = prototypes.get_npc_prototypes()
        assert reg["orc"]["desc"] == "Fierce orc"
