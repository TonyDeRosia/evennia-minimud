from unittest.mock import MagicMock, patch
from tempfile import TemporaryDirectory
from pathlib import Path
from unittest import mock

from django.test import override_settings
from django.conf import settings
from evennia.utils.test_resources import EvenniaTest

from commands.admin import BuilderCmdSet
from world import prototypes
from typeclasses.npcs import BaseNPC


@override_settings(DEFAULT_HOME=None)
class TestQuickMobCommand(EvenniaTest):
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
        if not hasattr(prototypes, "_normalize_proto"):
            prototypes._normalize_proto = prototypes._legacy._normalize_proto

    def test_quickmob_opens_builder(self):
        self.char1.location.set_area("town", 1)
        with (
            patch("utils.vnum_registry.get_next_vnum_for_area", return_value=101) as mock_vnum,
            patch("olc.base.EvMenu") as mock_menu,
        ):
            self.char1.execute_cmd("@quickmob goblin")

        mock_vnum.assert_called_with("town", "npc", builder=self.char1.key)
        mock_menu.assert_called()

        data = self.char1.ndb.buildnpc
        assert data["key"] == "goblin"
        assert data["vnum"] == 101
        assert data.get("use_mob") is True

        reg = prototypes.get_npc_prototypes()
        assert "mob_goblin" not in reg
        assert not any(o.is_typeclass(BaseNPC, exact=False) for o in self.char1.location.contents)
