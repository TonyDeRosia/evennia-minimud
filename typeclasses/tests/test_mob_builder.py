from unittest.mock import MagicMock, patch
from tempfile import TemporaryDirectory
from pathlib import Path
from unittest import mock

from django.test import override_settings
from django.conf import settings
from evennia.utils.test_resources import EvenniaTest

from commands.admin import BuilderCmdSet
from commands import mob_builder
from world import prototypes


@override_settings(DEFAULT_HOME=None)
class TestMobBuilder(EvenniaTest):
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

    def _find(self, key):
        for obj in self.char1.location.contents:
            if obj.key == key:
                return obj
        return None

    def test_builder_flow_and_spawn(self):
        with patch("commands.mob_builder.EvMenu"):
            self.char1.execute_cmd("mobbuilder")
        mob_builder._set_key(self.char1, "goblin")
        mob_builder._set_desc(self.char1, "A small goblin")
        mob_builder._set_level(self.char1, "1")
        mob_builder._set_class(self.char1, "warrior")
        mob_builder._set_race(self.char1, "orc")
        mob_builder._set_sex(self.char1, "male")
        mob_builder._set_hp(self.char1, "10")
        mob_builder._set_damage(self.char1, "2")
        mob_builder._set_armor(self.char1, "1")
        mob_builder._set_align(self.char1, "0")
        mob_builder._set_flags(self.char1, "")
        mob_builder._set_affects(self.char1, "")
        mob_builder._set_resists(self.char1, "")
        mob_builder._set_bodyparts(self.char1, "head arms")
        mob_builder._set_attack(self.char1, "punch")
        mob_builder._set_defense(self.char1, "parry")
        mob_builder._set_languages(self.char1, "common")
        mob_builder._set_role(self.char1, "")
        mob_builder._do_confirm(self.char1, "yes")

        reg = prototypes.get_npc_prototypes()
        assert "mob_goblin" in reg

        self.char1.execute_cmd("@mspawn mob_goblin")
        npc = self._find("goblin")
        assert npc is not None

        self.char1.execute_cmd("@mstat mob_goblin")
        out = self.char1.msg.call_args[0][0]
        assert "goblin" in out
