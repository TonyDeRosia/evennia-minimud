from unittest.mock import MagicMock, patch
from django.test import override_settings
from evennia.utils.test_resources import EvenniaTest
from commands.admin import BuilderCmdSet
from scripts.builder_autosave import BuilderAutosave


@override_settings(DEFAULT_HOME=None)
class TestBuilderAutosave(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.char1.msg = MagicMock()
        self.char1.cmdset.add_default(BuilderCmdSet)

    def test_restore_cnpc_session(self):
        with patch("commands.npc_builder.EvMenu") as mock_menu:
            self.char1.execute_cmd("mobbuilder start goblin")
            mock_menu.assert_called()
        script = self.char1.scripts.get("builder_autosave")[0]
        self.char1.ndb.buildnpc["desc"] = "A goblin"
        script.at_repeat()
        self.assertEqual(self.char1.db.builder_autosave["key"], "goblin")
        self.char1.ndb.buildnpc = None
        with patch("commands.npc_builder.EvMenu") as mock_menu:
            self.char1.execute_cmd("cnpc restore")
            mock_menu.assert_called()
        self.assertEqual(self.char1.ndb.buildnpc["desc"], "A goblin")
        self.assertIsNone(self.char1.db.builder_autosave)

    def test_restore_mobproto_session(self):
        from utils.mob_proto import register_prototype
        register_prototype({"key": "orc"}, vnum=1)
        with patch("commands.npc_builder.EvMenu") as mock_menu:
            self.char1.execute_cmd("@mobproto edit 1")
            mock_menu.assert_called()
        script = self.char1.scripts.get("builder_autosave")[0]
        self.char1.ndb.buildnpc["desc"] = "An orc"
        script.at_repeat()
        self.assertEqual(self.char1.db.builder_autosave["desc"], "An orc")
        self.char1.ndb.buildnpc = None
        with patch("commands.npc_builder.EvMenu") as mock_menu:
            self.char1.execute_cmd("@mobproto edit restore")
            mock_menu.assert_called()
        self.assertEqual(self.char1.ndb.buildnpc["desc"], "An orc")
        self.assertIsNone(self.char1.db.builder_autosave)

    def test_autosave_script_single_cnpc(self):
        with patch("commands.npc_builder.EvMenu"):
            self.char1.execute_cmd("mobbuilder start goblin")
        self.assertEqual(len(self.char1.scripts.get("builder_autosave")), 1)
        scr = self.char1.scripts.get("builder_autosave")[0]
        scr.at_repeat()
        self.char1.ndb.buildnpc = None
        with patch("commands.npc_builder.EvMenu"):
            self.char1.execute_cmd("cnpc restore")
        self.assertEqual(len(self.char1.scripts.get("builder_autosave")), 1)
        scr = self.char1.scripts.get("builder_autosave")[0]
        scr.at_repeat()
        self.char1.ndb.buildnpc = None
        with patch("commands.npc_builder.EvMenu"):
            self.char1.execute_cmd("cnpc restore")
        self.assertEqual(len(self.char1.scripts.get("builder_autosave")), 1)

    def test_autosave_script_single_mobproto(self):
        from utils.mob_proto import register_prototype
        register_prototype({"key": "orc"}, vnum=2)
        with patch("commands.npc_builder.EvMenu"):
            self.char1.execute_cmd("@mobproto edit 2")
        self.assertEqual(len(self.char1.scripts.get("builder_autosave")), 1)
        scr = self.char1.scripts.get("builder_autosave")[0]
        scr.at_repeat()
        self.char1.ndb.buildnpc = None
        with patch("commands.npc_builder.EvMenu"):
            self.char1.execute_cmd("@mobproto edit restore")
        self.assertEqual(len(self.char1.scripts.get("builder_autosave")), 1)
        scr = self.char1.scripts.get("builder_autosave")[0]
        scr.at_repeat()
        self.char1.ndb.buildnpc = None
        with patch("commands.npc_builder.EvMenu"):
            self.char1.execute_cmd("@mobproto edit restore")
        self.assertEqual(len(self.char1.scripts.get("builder_autosave")), 1)

