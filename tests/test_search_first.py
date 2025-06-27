from unittest.mock import MagicMock
from django.test import override_settings
from evennia.utils.test_resources import EvenniaTest
from evennia.utils import create
from typeclasses.rooms import Room
from typeclasses.objects import Corpse
from commands.default_cmdsets import CharacterCmdSet

@override_settings(DEFAULT_HOME=None)
class TestSearchFirst(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.char1.msg = MagicMock()
        self.char1.cmdset.add_default(CharacterCmdSet)
        self.room = create.create_object(
            Room, key="room", location=self.char1.location, home=self.char1.location
        )
        self.char1.location = self.room
        self.c1 = create.create_object(
            Corpse,
            key="corpse",
            location=self.room,
            attributes=[("corpse_of", "goblin1")],
        )
        self.c2 = create.create_object(
            Corpse,
            key="corpse",
            location=self.room,
            attributes=[("corpse_of", "goblin2")],
        )

    def test_look_picks_first_corpse(self):
        expected = self.c1.return_appearance(self.char1)
        self.char1.execute_cmd("look corpse")
        self.char1.msg.assert_any_call(expected)

    def test_numbered_alias_still_selects(self):
        expected = self.c2.return_appearance(self.char1)
        self.char1.msg.reset_mock()
        self.char1.execute_cmd("look corpse-2")
        self.char1.msg.assert_any_call(expected)
