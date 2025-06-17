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

    def test_cast(self):
        target = create_object(BaseNPC, key="target", location=self.room1)
        self.mob.cast_spell = MagicMock()
        execute_mpcommand(self.mob, "cast fireball target")
        self.mob.cast_spell.assert_called_with("fireball", target)

    def test_kill(self):
        enemy = create_object(BaseNPC, key="enemy", location=self.room1)
        self.mob.enter_combat = MagicMock()
        execute_mpcommand(self.mob, "kill enemy")
        self.mob.enter_combat.assert_called_with(enemy)

    def test_mpdamage(self):
        target = create_object(BaseNPC, key="victim", location=self.room1)
        target.at_damage = MagicMock()
        execute_mpcommand(self.mob, "mpdamage victim 5 fire")
        target.at_damage.assert_called_with(self.mob, 5, damage_type="fire")

    def test_mpapply(self):
        target = create_object(BaseNPC, key="victim", location=self.room1)
        with patch("world.system.state_manager.add_effect") as add_eff:
            execute_mpcommand(self.mob, "mpapply victim stunned 2")
            add_eff.assert_called_with(target, "stunned", 2)

    def test_mpcall(self):
        func = MagicMock()
        module = MagicMock()
        module.cb = func
        with patch("world.mpcommands.import_module", return_value=module) as mod:
            execute_mpcommand(self.mob, "mpcall scripts.mod.cb")
            mod.assert_called_with("scripts.mod")
            func.assert_called_with(self.mob)

    def test_mpcall_invalid_module(self):
        func = MagicMock()
        module = MagicMock()
        module.cb = func
        with patch("world.mpcommands.import_module", return_value=module) as mod:
            execute_mpcommand(self.mob, "mpcall bad.mod.cb")
            mod.assert_not_called()
            func.assert_not_called()

    def test_conditionals(self):
        self.room1.msg_contents = MagicMock()
        script = """if True\n    echo yes\nelse\n    echo no\nendif"""
        execute_mpcommand(self.mob, script)
        self.room1.msg_contents.assert_called_once_with("yes")

