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
class TestMSetCommand(EvenniaTest):
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

    def test_mset_edits_field(self):
        prototypes.register_npc_prototype("orc", {"key": "orc"})
        self.char1.execute_cmd('@mset orc desc "Fierce orc"')
        reg = prototypes.get_npc_prototypes()
        assert reg["orc"]["desc"] == "Fierce orc"

    def test_mset_loot_table(self):
        prototypes.register_npc_prototype("wolf", {"key": "wolf"})
        self.char1.execute_cmd('@mset wolf loot_table "[{\\"proto\\": \\"RAW_MEAT\\", \\"chance\\": 80}]"')
        reg = prototypes.get_npc_prototypes()
        table = reg["wolf"]["loot_table"]
        assert table[0]["proto"] == "RAW_MEAT"
        assert table[0]["chance"] == 80

    def test_mset_loot_table_guaranteed(self):
        prototypes.register_npc_prototype("boar", {"key": "boar"})
        self.char1.execute_cmd('@mset boar loot_table "[{\\"proto\\": \\"TUSK\\", \\"chance\\": 10, \\"guaranteed_after\\": 3}]"')
        reg = prototypes.get_npc_prototypes()
        table = reg["boar"]["loot_table"]
        assert table[0]["guaranteed_after"] == 3

    def test_mset_race_unique(self):
        prototypes.register_npc_prototype("beast", {"key": "beast"})
        self.char1.execute_cmd("@mset beast race unique")
        reg = prototypes.get_npc_prototypes()
        assert reg["beast"]["race"] == "unique"
