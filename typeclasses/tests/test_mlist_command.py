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

    def test_prototype_filtering(self):
        prototypes.register_npc_prototype(
            "orc_warrior",
            {"key": "orc warrior", "npc_class": "warrior", "race": "orc", "roles": ["guard"]},
        )
        prototypes.register_npc_prototype(
            "elf_mage",
            {"key": "elf mage", "npc_class": "mage", "race": "elf", "roles": ["questgiver"]},
        )
        res = prototypes.get_npc_prototypes({"class": "warrior"})
        assert list(res.keys()) == ["orc_warrior"]
        res = prototypes.get_npc_prototypes({"race": "elf"})
        assert list(res.keys()) == ["elf_mage"]
        res = prototypes.get_npc_prototypes({"role": "guard"})
        assert list(res.keys()) == ["orc_warrior"]

    def test_mlist_room_and_area(self):
        proto = {
            "key": "goblin",
            "npc_class": "warrior",
            "level": 1,
            "typeclass": "typeclasses.npcs.BaseNPC",
        }
        prototypes.register_npc_prototype("gob", proto)
        self.char1.execute_cmd("@spawnnpc gob")
        self.char1.execute_cmd("@mlist /room")
        out = self.char1.msg.call_args[0][0]
        assert "gob" in out
        self.char1.location.set_area("test", 1)
        self.char1.execute_cmd("dig north test 2")
        self.char1.location.db.exits.get("north")
        self.char1.execute_cmd("north")
        self.char1.execute_cmd("@spawnnpc gob")
        self.char1.execute_cmd("south")
        self.char1.execute_cmd("@mlist /area")
        out = self.char1.msg.call_args[0][0]
        assert "gob" in out
