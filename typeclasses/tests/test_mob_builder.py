from unittest.mock import MagicMock, patch
from tempfile import TemporaryDirectory
from pathlib import Path
from unittest import mock

from django.test import override_settings
from django.conf import settings
from evennia.utils.test_resources import EvenniaTest

from commands.admin import BuilderCmdSet
from commands import mob_builder, npc_builder
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
        with patch("commands.npc_builder.EvMenu") as mock_menu:
            self.char1.execute_cmd("mobbuilder")
            prompt = self.char1.msg.call_args[0][0]
            self.assertIn("Run", prompt)
            self.char1.msg.reset_mock()
            self.char1.execute_cmd("yes")
        mock_menu.assert_called()
        npc_builder._set_key(self.char1, "goblin")
        npc_builder._set_desc(self.char1, "A small goblin")
        npc_builder._set_creature_type(self.char1, "humanoid")
        npc_builder._set_role(self.char1, "")
        npc_builder._set_npc_class(self.char1, "base")
        npc_builder._edit_roles(self.char1, "done")
        npc_builder._set_level(self.char1, "1")
        npc_builder._set_resources(self.char1, "10 0 0")
        npc_builder._set_stats(self.char1, "1 1 1 1 1 1")
        npc_builder._set_behavior(self.char1, "")
        npc_builder._set_skills(self.char1, "")
        npc_builder._set_spells(self.char1, "")
        npc_builder._set_ai(self.char1, "passive")
        npc_builder._set_actflags(self.char1, "")
        npc_builder._set_affects(self.char1, "")
        npc_builder._set_resists(self.char1, "")
        npc_builder._set_bodyparts(self.char1, "head arms")
        npc_builder._set_attack(self.char1, "punch")
        npc_builder._set_defense(self.char1, "parry")
        npc_builder._set_languages(self.char1, "common")
        npc_builder._create_npc(self.char1, "", register=True)

        reg = prototypes.get_npc_prototypes()
        assert "mob_goblin" in reg
        assert reg["mob_goblin"]["typeclass"] == "typeclasses.npcs.BaseNPC"

        self.char1.execute_cmd("@mspawn mob_goblin")
        npc = self._find("goblin")
        assert npc is not None
        assert npc.is_typeclass(BaseNPC, exact=False)

        self.char1.execute_cmd("@mstat mob_goblin")
        out = self.char1.msg.call_args[0][0]
        assert "goblin" in out

    def test_cancel_then_back(self):
        """Cancellation should clear build data."""
        npc_builder._cancel(self.char1, "")
        assert self.char1.ndb.buildnpc is None
