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
class TestMCreateCommand(EvenniaTest):
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

    def test_mcreate_creates_prototype(self):
        self.char1.execute_cmd("@mcreate orc")
        reg = prototypes.get_npc_prototypes()
        assert "orc" in reg

    def test_mcreate_assigns_vnum_in_area(self):
        self.char1.location.set_area("town", 1)
        with mock.patch("utils.vnum_registry.get_next_vnum_for_area", return_value=55) as mock_vnum:
            self.char1.execute_cmd("@mcreate gob")
        mock_vnum.assert_called_with("town", "npc")
        reg = prototypes.get_npc_prototypes()
        assert reg["gob"]["vnum"] == 55
