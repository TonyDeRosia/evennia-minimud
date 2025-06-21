from unittest.mock import MagicMock, patch, ANY
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
        patcher4 = mock.patch.object(
            settings, "PROTOTYPE_NPC_FILE", Path(self.tmp.name) / "npcs.json"
        )
        self.addCleanup(self.tmp.cleanup)
        self.addCleanup(patcher1.stop)
        self.addCleanup(patcher2.stop)
        self.addCleanup(patcher3.stop)
        self.addCleanup(patcher4.stop)
        patcher1.start()
        patcher2.start()
        patcher3.start()
        patcher4.start()

    def test_medit_opens_builder_with_proto(self):
        from utils.mob_proto import register_prototype

        register_prototype({"key": "orc"}, vnum=5)
        with patch("commands.rom_mob_editor.EvMenu") as mock_menu:
            self.char1.execute_cmd("medit 5")
            mock_menu.assert_called_with(
                self.char1,
                "commands.rom_mob_editor",
                startnode="menunode_main",
                cmd_on_exit=ANY,
            )
        data = self.char1.ndb.mob_proto
        assert data["key"] == "orc"
        assert self.char1.ndb.mob_vnum == 5

    def test_medit_create(self):
        with (
            patch("commands.rom_mob_editor.EvMenu") as mock_menu,
            patch("commands.rom_mob_editor.get_template", return_value={"level": 2}),
        ):
            self.char1.execute_cmd("medit create 10")
            mock_menu.assert_called_with(
                self.char1,
                "commands.rom_mob_editor",
                startnode="menunode_main",
                cmd_on_exit=ANY,
            )
        data = self.char1.ndb.mob_proto
        assert data["level"] == 2
        assert self.char1.ndb.mob_vnum == 10

    def test_medit_registered_proto(self):
        from utils.mob_proto import register_prototype

        register_prototype({"key": "troll"}, vnum=7)
        with patch("commands.rom_mob_editor.EvMenu") as mock_menu:
            self.char1.execute_cmd("medit 7")
            mock_menu.assert_called_with(
                self.char1,
                "commands.rom_mob_editor",
                startnode="menunode_main",
                cmd_on_exit=ANY,
            )
        data = self.char1.ndb.mob_proto
        assert data["key"] == "troll"
        assert self.char1.ndb.mob_vnum == 7

    def test_rom_menu_has_loot_option(self):
        from commands import rom_mob_editor

        self.char1.ndb.mob_proto = {}
        self.char1.ndb.mob_vnum = 1
        _, options = rom_mob_editor.menunode_main(self.char1)
        gotos = [opt.get("goto") for opt in options]
        assert "menunode_loot" in gotos
        assert "menunode_skills" in gotos
        assert "menunode_spells" in gotos
        assert gotos[-2:] == ["menunode_cancel", "menunode_done"]

    def test_inventory_and_equipment_editors(self):
        from commands import rom_mob_editor

        self.char1.ndb.mob_proto = {}
        with patch(
            "commands.rom_mob_editor.load_prototype", return_value={"key": "obj"}
        ):
            rom_mob_editor._edit_inventory(self.char1, "add 100001")
            assert self.char1.ndb.mob_proto["inventory"] == [100001]
            rom_mob_editor._edit_inventory(self.char1, "remove 100001")
            assert self.char1.ndb.mob_proto["inventory"] == []

            rom_mob_editor._edit_equipment(self.char1, "add 100002")
            assert self.char1.ndb.mob_proto["equipment"] == [100002]
            rom_mob_editor._edit_equipment(self.char1, "remove 100002")
            assert self.char1.ndb.mob_proto["equipment"] == []

    def test_menu_save_writes_script_and_json(self):
        from commands import rom_mob_editor
        from world.scripts.mob_db import get_mobdb
        import json

        proto = {"key": "ogre", "desc": "big"}
        self.char1.ndb.mob_proto = dict(proto)
        self.char1.ndb.mob_vnum = 42

        result = rom_mob_editor.menunode_done(self.char1)
        assert result is None

        mob_db = get_mobdb()
        assert mob_db.get_proto(42)["key"] == "ogre"

        path = Path(settings.PROTOTYPE_NPC_FILE)
        with path.open() as f:
            data = json.load(f)
        assert "ogre" in data

    def test_medit_string_vnum_lookup(self):
        """Editing should work if the prototype is stored under a string key."""
        from world.scripts.mob_db import get_mobdb

        mob_db = get_mobdb()
        mob_db.db.vnums["5"] = {"key": "orc", "vnum": 5}

        with patch("commands.rom_mob_editor.EvMenu") as mock_menu:
            self.char1.execute_cmd("medit 5")
            mock_menu.assert_called_with(
                self.char1,
                "commands.rom_mob_editor",
                startnode="menunode_main",
                cmd_on_exit=ANY,
            )
        assert self.char1.ndb.mob_vnum == 5
        assert self.char1.ndb.mob_proto["key"] == "orc"

    def test_medit_not_found_message(self):
        """Missing prototypes should show a helpful message."""
        self.char1.msg.reset_mock()
        self.char1.execute_cmd("medit 999")
        out = self.char1.msg.call_args[0][0]
        assert "Prototype 999 not found." in out

    def test_medit_create_duplicate_vnum(self):
        from utils.mob_proto import register_prototype

        register_prototype({"key": "gob"}, vnum=10)
        self.char1.msg.reset_mock()
        self.char1.execute_cmd("medit create 10")
        out = self.char1.msg.call_args[0][0]
        assert "Invalid or already used VNUM" in out

    def test_cancel_new_proto_prompts_and_leaves_vnum_free(self):
        from utils import vnum_registry
        from commands import rom_mob_editor

        self.char1.ndb.mob_proto = {}
        self.char1.ndb.mob_vnum = 10
        self.char1.ndb.mob_saved = False

        result = rom_mob_editor.menunode_cancel(self.char1)
        assert result == "menunode_unsaved_prompt"
        assert vnum_registry.validate_vnum(10, "npc")

    def test_on_exit_unsaved_opens_prompt(self):
        from commands import rom_mob_editor

        self.char1.ndb.mob_proto = {}
        self.char1.ndb.mob_vnum = 11
        self.char1.ndb.mob_saved = False

        with patch("commands.rom_mob_editor.EvMenu") as mock_menu:
            rom_mob_editor._on_exit(self.char1, None)
            mock_menu.assert_called_with(
                self.char1,
                "commands.rom_mob_editor",
                startnode="menunode_unsaved_prompt",
            )
