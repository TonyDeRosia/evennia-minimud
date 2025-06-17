import json
from unittest.mock import patch, MagicMock
from tempfile import TemporaryDirectory
from pathlib import Path
from django.test import override_settings
from evennia.utils.test_resources import EvenniaTest
from commands.admin import BuilderCmdSet
from commands import redit
from typeclasses.rooms import Room
from evennia.utils import create


@override_settings(DEFAULT_HOME=None)
class TestREditAreaFile(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.tmp = TemporaryDirectory()
        patcher_area = patch('world.areas._BASE_PATH', Path(self.tmp.name))
        patcher_proto = patch.dict('utils.prototype_manager.CATEGORY_DIRS', {'room': Path(self.tmp.name)})
        self.addCleanup(self.tmp.cleanup)
        self.addCleanup(patcher_area.stop)
        self.addCleanup(patcher_proto.stop)
        patcher_area.start()
        patcher_proto.start()
        self.char1.msg = MagicMock()
        self.char1.cmdset.add_default(BuilderCmdSet)
        self.char1.execute_cmd('amake zone 1-10')
        self.area_file = Path(self.tmp.name) / 'zone.json'
        self.char1.msg.reset_mock()

    def test_room_saved_to_area(self):
        room = create.create_object(Room, key='Room', location=self.char1.location, home=self.char1.location)
        room.db.room_id = 3
        room.db.area = 'zone'
        self.char1.location = room
        with patch('commands.redit.load_prototype', return_value=None), \
             patch('commands.redit.OLCEditor') as mock_editor, \
             patch('commands.redit.ObjectDB.objects.filter', return_value=[room]):
            self.char1.execute_cmd('redit 3')
            mock_editor.assert_called()
        with patch('commands.redit.save_prototype'):
            redit.menunode_done(self.char1)
        with self.area_file.open() as f:
            data = json.load(f)
        assert 3 in data.get('rooms', [])
