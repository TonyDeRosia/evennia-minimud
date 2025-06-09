from unittest.mock import MagicMock
from evennia.utils import create
from evennia.utils.test_resources import EvenniaTest


class TestRoomTriggers(EvenniaTest):
    def test_enter_leave_and_look(self):
        room = self.room1
        room.check_triggers = MagicMock()
        self.char2.location = self.room2
        self.char2.move_to(room)
        room.check_triggers.assert_any_call("on_enter", obj=self.char2, source=self.room2)
        room.check_triggers.reset_mock()
        self.char2.move_to(self.room2)
        room.check_triggers.assert_any_call("on_leave", obj=self.char2, destination=self.room2)
        room.check_triggers.reset_mock()
        room.return_appearance(self.char1)
        room.check_triggers.assert_any_call("on_look", looker=self.char1)


class TestObjectTriggers(EvenniaTest):
    def test_look_and_use(self):
        obj = create.create_object("typeclasses.objects.Object", key="widget")
        obj.check_triggers = MagicMock()
        obj.return_appearance(self.char1)
        obj.check_triggers.assert_any_call("on_look", looker=self.char1)
        obj.check_triggers.reset_mock()
        obj.at_use(self.char1)
        obj.check_triggers.assert_any_call("on_use", user=self.char1)

