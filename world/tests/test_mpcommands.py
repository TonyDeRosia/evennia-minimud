from unittest.mock import MagicMock, patch
from evennia.utils.test_resources import EvenniaTest
from evennia import create_object
from world.mpcommands import execute_mpcommand
from typeclasses.npcs import BaseNPC


class TestMPCommands(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.mob = create_object(BaseNPC, key="mob", location=self.room1)

    def test_echo(self):
        self.room1.msg_contents = MagicMock()
        execute_mpcommand(self.mob, "echo Hello")
        self.room1.msg_contents.assert_called_with("Hello")

    def test_goto(self):
        dest = create_object("typeclasses.rooms.Room", key="dest")
        execute_mpcommand(self.mob, "goto dest")
        self.assertEqual(self.mob.location, dest)

    def test_mload(self):
        with patch("utils.mob_proto.spawn_from_vnum") as mock_spawn:
            execute_mpcommand(self.mob, "mload 5")
            mock_spawn.assert_called_with(5, location=self.mob.location)

