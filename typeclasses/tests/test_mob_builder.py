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
        npc_builder._set_race(self.char1, "human")
        npc_builder._set_npc_class(self.char1, "base")
        npc_builder._set_sex(self.char1, "male")
        npc_builder._set_weight(self.char1, "medium")
        npc_builder._set_level(self.char1, "1")
        npc_builder._set_vnum(self.char1, "auto")
        npc_builder._set_creature_type(self.char1, "humanoid")
        npc_builder._set_role(self.char1, "")
        npc_builder._set_combat_class(self.char1, "Warrior")
        npc_builder._edit_roles(self.char1, "done")
        npc_builder._set_exp_reward(self.char1, "5")
        npc_builder._set_coin_drop(self.char1, "1 gold")
        npc_builder._edit_loot_table(self.char1, "add RAW_MEAT 50")
        npc_builder._edit_loot_table(self.char1, "done")
        npc_builder._set_resources(self.char1, "10 0 0")
        npc_builder._set_modifiers(self.char1, "skip")
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
        assert npc.db.charclass == "Warrior"

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
            "race": "orc",
            "sex": "male",
            "weight": "small",
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
            "|cMob Prototype:",
            "|cBasic Info|n",
            "|cCombat Stats|n",
            "|cCombat Flags|n",
            "|cRewards|n",
            "|cSkills|n",
        ]:
            assert text in out
        assert "slash" in out
        assert "gold" in out
        assert "RAW_MEAT" in out

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

    def test_npc_class_menu_shows_next(self):
        """menunode_npc_class should offer a Next option."""
        self.char1.ndb.buildnpc = {}
        _text, opts = npc_builder.menunode_npc_class(self.char1)
        labels = [o.get("desc") or o.get("key") for o in opts]
        assert "Next" in labels
        assert "Skip" not in labels

    def test_combat_class_menu_shows_next(self):
        """menunode_combat_class should offer a Next option."""
        self.char1.ndb.buildnpc = {}
        _text, opts = npc_builder.menunode_combat_class(self.char1)
        labels = [o.get("desc") or o.get("key") for o in opts]
        assert "Next" in labels
        assert "Skip" not in labels

    def test_custom_slots_menu_shows_next(self):
        """menunode_custom_slots should offer a Next option."""
        self.char1.ndb.buildnpc = {}
        _text, opts = npc_builder.menunode_custom_slots(self.char1)
        labels = [o.get("desc") or o.get("key") for o in opts]
        assert "Next" in labels
        assert "Skip" not in labels

    def test_skills_menu_shows_suggestions(self):
        """menunode_skills should list suggested skills for the class."""
        self.char1.ndb.buildnpc = {"npc_class": "combat_trainer"}
        text, _ = npc_builder.menunode_skills(self.char1)
        for skill in npc_builder.DEFAULT_SKILLS:
            assert skill in text

    def test_set_coin_drop(self):
        self.char1.ndb.buildnpc = {}
        result = npc_builder._set_coin_drop(self.char1, "1 gold 2 silver")
        assert self.char1.ndb.buildnpc["coin_drop"] == {"gold": 1, "silver": 2}
        assert result == "menunode_loot_table"

    def test_edit_loot_table(self):
        self.char1.ndb.buildnpc = {}
        npc_builder._edit_loot_table(self.char1, "add RAW_MEAT 75")
        assert self.char1.ndb.buildnpc["loot_table"] == [{"proto": "RAW_MEAT", "chance": 75}]
        result = npc_builder._edit_loot_table(self.char1, "done")
        assert result == "menunode_resources_prompt"

    def test_exp_reward_back_returns_to_level(self):
        """Entering back at exp reward should return to level menu."""
        self.char1.ndb.buildnpc = {"level": 1}
        result = npc_builder._set_exp_reward(self.char1, "back")
        assert result == "menunode_role_details"

    def test_resources_back_returns_to_prompt(self):
        """Entering back at resources should return to resources prompt."""
        self.char1.ndb.buildnpc = {}
        result = npc_builder._set_resources(self.char1, "back")
        assert result == "menunode_resources_prompt"

    def test_secondary_stats_prompt_options(self):
        self.char1.ndb.buildnpc = {}
        _text, opts = npc_builder.menunode_secondary_stats_prompt(self.char1)
        gotos = [o.get("goto") for o in opts]
        assert "menunode_stats" in gotos
        assert "menunode_modifiers" in gotos

    def test_use_default_stats_skips_stat_entry(self):
        self.char1.ndb.buildnpc = {}
        result = npc_builder._use_default_stats(self.char1, "")
        assert result == "menunode_behavior"
        assert self.char1.ndb.buildnpc["primary_stats"] == {
            stat: 0 for stat in ["STR", "CON", "DEX", "INT", "WIS", "LUCK"]
        }

    def test_modifiers_skip_leads_to_secondary_prompt(self):
        self.char1.ndb.buildnpc = {}
        result = npc_builder._set_modifiers(self.char1, "skip")
        assert result == "menunode_secondary_stats_prompt"

    def test_summary_shows_coin_and_loot(self):
        data = {
            "key": "orc",
            "coin_drop": {"gold": 2},
            "loot_table": [{"proto": "RAW_MEAT", "chance": 50}],
        }
        out = npc_builder.format_mob_summary(data)
        assert "gold" in out
        assert "RAW_MEAT" in out

    def test_confirm_requires_missing_fields(self):
        self.char1.msg = MagicMock()
        self.char1.ndb.buildnpc = {
            "key": "orc",
            "level": 1,
            "vnum": 5,
            "creature_type": "humanoid",
            "role": "merchant",
        }
        result = npc_builder.menunode_confirm(self.char1)
        self.assertEqual(result, "menunode_desc")
        msg = self.char1.msg.call_args[0][0]
        self.assertIn("Description is required", msg)

    def test_confirm_full_data_options(self):
        self.char1.ndb.buildnpc = {
            "key": "orc",
            "desc": "mean orc",
            "level": 2,
            "vnum": 7,
            "creature_type": "humanoid",
            "role": "merchant",
        }
        text, opts = npc_builder.menunode_confirm(self.char1)
        labels = [o.get("desc") or o.get("key") for o in opts]
        assert set(labels) == {"Yes", "Yes & Save Prototype", "No"}

