from unittest.mock import MagicMock, patch
from tempfile import TemporaryDirectory
from pathlib import Path
from unittest import mock

from django.test import override_settings
from django.conf import settings
from evennia.utils.test_resources import EvenniaTest

from commands.admin import BuilderCmdSet
from utils import prototype_manager, vnum_registry
from commands import npc_builder


@override_settings(DEFAULT_HOME=None)
class TestMEditCommand(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.char1.msg = MagicMock()
        self.char1.cmdset.add_default(BuilderCmdSet)
        self.tmp = TemporaryDirectory()
        patcher1 = mock.patch.dict(
            prototype_manager.CATEGORY_DIRS, {"npc": Path(self.tmp.name)}
        )
        patcher2 = mock.patch.object(
            settings, "VNUM_REGISTRY_FILE", Path(self.tmp.name) / "vnums.json"
        )
        patcher3 = mock.patch.object(
            vnum_registry, "_REG_PATH", Path(self.tmp.name) / "vnums.json"
        )
        self.addCleanup(self.tmp.cleanup)
        self.addCleanup(patcher1.stop)
        self.addCleanup(patcher2.stop)
        self.addCleanup(patcher3.stop)
        patcher1.start()
        patcher2.start()
        patcher3.start()

    def test_medit_opens_builder_with_proto(self):
        prototype_manager.save_prototype("npc", {"key": "orc"}, vnum=5)
        with patch("commands.medit.EvMenu") as mock_menu:
            self.char1.execute_cmd("medit 5")
            mock_menu.assert_called_with(
                self.char1,
                "commands.npc_builder",
                startnode="menunode_key",
                cmd_on_exit=npc_builder._on_menu_exit,
            )
        data = self.char1.ndb.buildnpc
        assert data["key"] == "orc"
        assert self.char1.ndb.mob_vnum == 5
