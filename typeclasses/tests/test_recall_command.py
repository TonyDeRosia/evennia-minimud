from unittest.mock import MagicMock
from django.test import override_settings
from evennia.utils.test_resources import EvenniaTest
from commands.skills.recall import CmdRecall
from world.scripts import create_midgard_area
from evennia.objects.models import ObjectDB
from typeclasses.rooms import Room


@override_settings(DEFAULT_HOME=None)
class TestRecallCommand(EvenniaTest):
    def setUp(self):
        super().setUp()
        create_midgard_area.create()
        self.char1.msg = MagicMock()
        self.cmd = CmdRecall()
        self.cmd.caller = self.char1
        self.cmd.msg = self.char1.msg

    def test_refuses_without_mana(self):
        self.char1.traits.mana.current = 5
        self.cmd.func()
        self.char1.msg.assert_called_with("You do not have enough mana.")
        self.assertEqual(self.char1.location, self.room1)

    def test_successful_recall(self):
        mana_before = self.char1.traits.mana.current
        self.cmd.func()
        objs = ObjectDB.objects.filter(
            db_attributes__db_key="room_id", db_attributes__db_value=200050
        )
        dest = None
        for obj in objs:
            if obj.is_typeclass(Room, exact=False):
                dest = obj
                break
        self.assertEqual(self.char1.location, dest)
        self.assertEqual(self.char1.traits.mana.current, mana_before - 10)
        self.assertTrue(self.char1.cooldowns.time_left("recall", use_int=True))

