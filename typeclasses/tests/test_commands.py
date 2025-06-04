"""Tests for custom commands."""

from unittest.mock import MagicMock

from evennia.utils.test_resources import EvenniaTest


class TestInfoCommands(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.char1.msg = MagicMock()
        self.char2.msg = MagicMock()
        self.obj1.location = self.char1
        self.char1.db.desc = "A tester."
        self.char2.db.desc = "Another tester."

    def test_desc_set_and_view(self):
        self.char1.execute_cmd("desc")
        self.assertTrue(self.char1.msg.called)
        self.char1.msg.reset_mock()
        self.char1.execute_cmd("desc New description")
        self.assertEqual(self.char1.db.desc, "New description")

    def test_finger(self):
        self.char1.execute_cmd(f"finger {self.char2.key}")
        self.assertTrue(self.char1.msg.called)

    def test_score(self):
        self.char1.execute_cmd("score")
        self.assertTrue(self.char1.msg.called)

    def test_stats_alias_sc(self):
        self.char1.execute_cmd("sc")
        self.assertTrue(self.char1.msg.called)

    def test_inventory(self):
        self.char1.execute_cmd("inventory")
        self.assertTrue(self.char1.msg.called)
        self.char1.msg.reset_mock()
        self.obj1.location = self.char1
        self.char1.execute_cmd("inventory")
        self.assertTrue(self.char1.msg.called)

    def test_equipment(self):
        self.char1.attributes.add("_wielded", {"left": self.obj1})
        self.char1.execute_cmd("equipment")
        self.assertTrue(self.char1.msg.called)

    def test_buffs(self):
        self.char1.execute_cmd("buffs")
        self.assertTrue(self.char1.msg.called)
        self.char1.msg.reset_mock()
        self.char1.tags.add("speed", category="buff")
        self.char1.execute_cmd("buffs")
        self.assertTrue(self.char1.msg.called)

    def test_guild(self):
        self.char1.db.guild = "Adventurers Guild"
        self.char1.execute_cmd("guild")
        self.assertTrue(self.char1.msg.called)

    def test_guildwho(self):
        self.char1.db.guild = "Adventurers Guild"
        self.char2.db.guild = "Adventurers Guild"
        self.char1.execute_cmd("guildwho")
        self.assertTrue(self.char1.msg.called)

