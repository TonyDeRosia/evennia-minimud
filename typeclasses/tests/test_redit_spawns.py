from unittest.mock import patch, MagicMock
from django.test import override_settings
from evennia.utils.test_resources import EvenniaTest
from evennia.utils import create
from typeclasses.rooms import Room
from commands import redit
from commands.admin import BuilderCmdSet


@override_settings(DEFAULT_HOME=None)
class TestReditSpawns(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.char1.msg = MagicMock()
        self.char1.cmdset.add_default(BuilderCmdSet)

    def test_spawn_edit_keeps_exits(self):
        room1 = create.create_object(Room, key="R1", location=self.char1.location, home=self.char1.location)
        room2 = create.create_object(Room, key="R2", location=self.char1.location, home=self.char1.location)
        room1.db.room_id = 5
        room2.db.room_id = 6
        room1.db.area = "zone"
        room2.db.area = "zone"
        room1.db.exits = {"north": room2}
        self.char1.location = room1

        with patch("commands.redit.load_prototype", return_value=None), patch("commands.redit.OLCEditor"):
            self.char1.execute_cmd("redit 5")

        proto = self.char1.ndb.room_protos[5]
        assert proto["exits"] == {"north": 6}
        proto.setdefault("spawns", []).append({
            "prototype": "goblin",
            "max_spawns": 2,
            "spawn_interval": 10,
            "location": 5,
        })
        self.char1.ndb.room_protos[5] = proto

        with patch("commands.redit.save_prototype") as mock_save:
            redit.menunode_done(self.char1)
            mock_save.assert_called()
            saved = mock_save.call_args[0][1]
            assert saved["exits"] == {"north": 6}

        assert room1.db.exits == {"north": room2}

    def test_register_room_spawn_uses_proto_vnum(self):
        room = create.create_object(Room, key="R1", location=self.char1.location, home=self.char1.location)
        room.db.room_id = 5
        room.db.area = "zone"
        self.char1.location = room

        with patch("commands.redit.load_prototype", return_value=None), patch("commands.redit.OLCEditor"):
            self.char1.execute_cmd("redit 5")

        proto = self.char1.ndb.room_protos[5]
        proto["spawns"] = [{"prototype": "goblin"}]
        self.char1.ndb.room_protos[5] = proto

        mock_script = MagicMock()
        with patch("commands.redit.save_prototype"), patch(
            "commands.redit.ObjectDB.objects.filter", return_value=[room]
        ), patch("commands.redit.ScriptDB.objects.filter") as mock_filter:
            mock_filter.return_value.first.return_value = mock_script
            redit.menunode_done(self.char1)
            mock_script.register_room_spawn.assert_called_with(proto)
            assert proto["vnum"] == 5

