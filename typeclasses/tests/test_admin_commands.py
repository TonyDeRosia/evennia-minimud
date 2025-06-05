from unittest.mock import MagicMock

from evennia import create_object
from commands.admin import AdminCmdSet
from commands.default_cmdsets import CharacterCmdSet
from evennia.utils.test_resources import EvenniaTest
from django.test import override_settings
from typeclasses.characters import PlayerCharacter
from typeclasses.objects import Object


@override_settings(DEFAULT_HOME=None)
class TestAdminCommands(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.char1.msg = MagicMock()
        self.char2.msg = MagicMock()
        # ensure commands are available even when characters are offline
        self.char1.cmdset.add_default(AdminCmdSet)
        self.char2.cmdset.add_default(AdminCmdSet)
        # extra room setup for scan command
        self.room2.db.desc = "Another room"
        self.room2.tags.add("dark", category="room_flag")
        self.room2.tags.add("ruins")
        self.obj1.location = self.room2
        self.char_other = create_object(
            PlayerCharacter, key="OtherChar", location=self.room2, home=self.room2
        )
        self.char_other.cmdset.add_default(CharacterCmdSet)

    def test_setstat_and_setattr_offline(self):
        offline = create_object(PlayerCharacter, key="Offline", location=self.room1, home=self.room1)
        self.char1.execute_cmd(f"setstat {offline.key} STR 15")
        self.assertEqual(offline.traits.STR.base, 15)
        self.char1.execute_cmd(f"setattr {offline.key} foo bar")
        self.assertEqual(offline.db.foo, "bar")

    def test_slay_clears_bounty(self):
        self.char2.db.bounty = 10
        self.char1.execute_cmd(f"slay {self.char2.key}")
        self.assertEqual(self.char2.traits.health.current, 0)
        self.assertTrue(self.char2.tags.has("unconscious", category="status"))
        self.assertEqual(self.char2.db.bounty, 0)

    def test_smite(self):
        self.char2.traits.health.current = 20
        self.char1.execute_cmd(f"smite {self.char2.key}")
        self.assertEqual(self.char2.traits.health.current, 1)

    def test_scan_player_vs_admin(self):
        self.char2.execute_cmd("scan")
        player_out = self.char2.msg.call_args[0][0]
        self.assertNotIn("Room flags:", player_out)
        self.assertNotIn("Tags:", player_out)
        self.char1.execute_cmd("scan")
        admin_out = self.char1.msg.call_args[0][0]
        self.assertIn("Room flags: dark", admin_out)
        self.assertIn("Tags: ruins", admin_out)
        self.assertIn("HP", admin_out)

    def test_help_entries_exist(self):
        for cmd in ("slay", "smite", "setstat", "setattr", "scan", "restoreall"):
            self.char1.msg.reset_mock()
            self.char1.execute_cmd(f"help {cmd}")
            self.assertTrue(self.char1.msg.called)

    def test_restoreall(self):
        self.char1.traits.health.current = 10
        self.char2.traits.mana.current = 5
        self.char1.tags.add("speed", category="buff")
        self.char2.tags.add("sleeping", category="status")
        self.char_other.traits.stamina.current = 1
        self.char1.execute_cmd("restoreall")
        for pc in (self.char1, self.char2, self.char_other):
            self.assertEqual(pc.traits.health.current, pc.traits.health.max)
            self.assertEqual(pc.traits.mana.current, pc.traits.mana.max)
            self.assertEqual(pc.traits.stamina.current, pc.traits.stamina.max)
            self.assertFalse(pc.tags.get(category="buff", return_list=True))
            self.assertFalse(pc.tags.get(category="status", return_list=True))


    def test_revive_all(self):
        for pc in (self.char2, self.char_other):
            pc.tags.add("unconscious", category="status")
            pc.tags.add("lying down", category="status")
            pc.traits.health.current = 0
        from commands.combat import CmdRevive
        cmd = CmdRevive()
        cmd.caller = self.char1
        cmd.args = "all"
        cmd.msg = MagicMock()
        cmd.func()
        for pc in (self.char2, self.char_other):
            self.assertFalse(pc.tags.has("unconscious", category="status"))
            self.assertEqual(pc.traits.health.current, pc.traits.health.max // 5)

    def test_purge_deletes_objects(self):
        obj1 = create_object(Object, key="trash", location=self.room1)
        obj2 = create_object(Object, key="garbage", location=self.room1)
        self.char1.location = self.room1
        self.char1.execute_cmd("purge")
        self.assertIsNone(obj1.pk)
        self.assertIsNone(obj2.pk)

    def test_purge_target(self):
        obj = create_object(Object, key="target", location=self.room1)
        self.char1.execute_cmd("purge target")
        self.assertIsNone(obj.pk)
