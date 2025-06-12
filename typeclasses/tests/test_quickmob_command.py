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

    def test_quickmob_creates_and_spawns(self):
        self.char1.location.set_area("town", 1)
        with patch("utils.vnum_registry.get_next_vnum_for_area", return_value=101) as mock_vnum:
            self.char1.execute_cmd("@quickmob goblin")
        mock_vnum.assert_called_with("town", "npc", builder=self.char1.key)
        reg = prototypes.get_npc_prototypes()
        assert "mob_goblin" in reg
        assert reg["mob_goblin"]["vnum"] == 101
        npc = [o for o in self.char1.location.contents if o.is_typeclass(BaseNPC, exact=False)][0]
        assert npc.key == "goblin"
        assert npc.db.vnum == 101
        assert npc.db.charclass == "Warrior"
        assert npc.db.hp > 0
        self.char1.msg.reset_mock()
        self.char1.execute_cmd("@mspawn M101")
        msg = self.char1.msg.call_args[0][0]
        assert "Spawned" in msg
        assert any(o.db.vnum == 101 for o in self.char1.location.contents)
