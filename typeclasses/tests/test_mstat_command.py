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
class TestMStatCommand(EvenniaTest):
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

    def test_mstat_displays_stats(self):
        prototypes.register_npc_prototype("orc", {"key": "orc", "desc": "mean"})
        self.char1.execute_cmd("@mstat orc")
        out = self.char1.msg.call_args[0][0]
        assert "orc" in out
        assert "mean" in out
        assert "Flags" in out
        assert "Saves" in out
        assert "Attacks" in out
        assert "Defenses" in out
        assert "Resists" in out
        assert "Languages" in out

    def test_mstat_rom_switch(self):
        prototypes.register_npc_prototype(
            "orc",
            {
                "key": "orc",
                "level": 3,
                "race": "orc",
                "npc_type": "warrior",
                "damage": 2,
                "actflags": ["aggressive"],
            },
        )
        self.char1.execute_cmd("@mstat /rom orc")
        out = self.char1.msg.call_args[0][0]
        assert "Level: 3" in out
        assert "Race: orc" in out
        assert "Damage" in out
        assert "aggressive" in out
