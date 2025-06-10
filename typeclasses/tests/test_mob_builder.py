from unittest.mock import MagicMock, patch
from tempfile import TemporaryDirectory
from pathlib import Path
from unittest import mock

from django.test import override_settings
from django.conf import settings
from evennia.utils.test_resources import EvenniaTest

from commands.admin import BuilderCmdSet
from commands import npc_builder
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
            self.char1.execute_cmd("mobbuilder start goblin")
        mock_menu.assert_called_with(
            self.char1, "commands.npc_builder", startnode="menunode_desc"
        )
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

    def test_summary_contains_sections(self):
        """format_mob_summary should include key headings and data."""
        data = {
            "key": "goblin",
            "desc": "A nasty goblin",
            "level": 2,
            "hp": 10,
            "mp": 0,
            "sp": 0,
            "primary_stats": {"STR": 1, "CON": 1},
            "actflags": ["aggressive"],
            "affected_by": ["invisible"],
            "ris": ["fire"],
            "exp_reward": 5,
            "coin_drop": {"gold": 1},
            "loot_table": [{"proto": "RAW_MEAT", "chance": 50}],
            "skills": ["slash"],
            "spells": ["heal"],
        }
        out = npc_builder.format_mob_summary(data)
        for text in [
            "Mob Prototype:",
            "Basic Info",
            "Combat Stats",
            "Combat Flags",
            "Rewards",
            "Skills",
        ]:
            assert text in out
        assert "slash" in out

    def test_vnum_menu_without_existing(self):
        """When no VNUM is set, Skip should not appear and Auto option is shown."""
        self.char1.ndb.buildnpc = {}
        _text, opts = npc_builder.menunode_vnum(self.char1)
        labels = [o.get("desc") or o.get("key") for o in opts]
        assert "Skip" not in labels
        assert any(o.get("desc") == "Auto" for o in opts)

    def test_set_vnum_auto(self):
        """Selecting auto should store the generated VNUM."""
        self.char1.ndb.buildnpc = {}
        with patch("utils.vnum_registry.get_next_vnum", return_value=42) as mock:
            result = npc_builder._set_vnum(self.char1, "auto")
        mock.assert_called_with("npc")
        assert self.char1.ndb.buildnpc["vnum"] == 42
        assert result == "menunode_creature_type"

    def test_set_vnum_skip_existing(self):
        """Skipping with an existing VNUM keeps the value."""
        self.char1.ndb.buildnpc = {"vnum": 5}
        result = npc_builder._set_vnum(self.char1, "skip")
        assert self.char1.ndb.buildnpc["vnum"] == 5
        assert result == "menunode_creature_type"
