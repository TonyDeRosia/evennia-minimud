from unittest.mock import MagicMock, patch
from tempfile import TemporaryDirectory
from pathlib import Path
from evennia.utils.test_resources import EvenniaTest
from evennia import create_object

from typeclasses.rooms import Room
from commands.building import CmdRDel
from utils.prototype_manager import CATEGORY_DIRS


class TestRDelCommand(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.tmp = TemporaryDirectory()
        patcher = patch.dict('utils.prototype_manager.CATEGORY_DIRS', {'room': Path(self.tmp.name)})
        self.addCleanup(self.tmp.cleanup)
        self.addCleanup(patcher.stop)
        patcher.start()
        self.char1.msg = MagicMock()

    def test_rdel_deletes_room_and_proto(self):
        room = create_object(Room, key='R', location=self.room1)
        room.set_area('zone', 5)
        self.room1.db.exits = {'north': room}
        room.db.exits = {'south': self.room1}
        proto_path = CATEGORY_DIRS['room'] / '5.json'
        proto_path.parent.mkdir(parents=True, exist_ok=True)
        proto_path.write_text('{"vnum": 5}')

        cmd = CmdRDel()
        cmd.caller = self.char1
        cmd.args = '5'
        cmd.msg = MagicMock()
        cmd.func()

        cmd.msg.assert_called_with('Room 5 deleted.')
        self.assertIsNone(room.pk)
        self.assertNotIn('north', self.room1.db.exits)
        self.assertFalse(proto_path.exists())

    def test_usage(self):
        cmd = CmdRDel()
        cmd.caller = self.char1
        cmd.args = 'abc'
        cmd.msg = MagicMock()
        cmd.func()
        cmd.msg.assert_called_with('Usage: rdel <vnum>')
