from unittest.mock import MagicMock, patch
from evennia.utils.test_resources import EvenniaTest
from django.test import override_settings
from commands.admin import BuilderCmdSet
from commands.areas import AreaCmdSet


@override_settings(DEFAULT_HOME=None)
class TestREditCommand(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.char1.msg = MagicMock()
        self.char1.cmdset.add_default(BuilderCmdSet)
        self.char1.cmdset.add_default(AreaCmdSet)

    def test_open_existing_proto(self):
        with (
            patch("commands.redit.load_prototype", return_value={"vnum": 5}) as mock_load,
            patch("commands.redit.OLCEditor") as mock_editor,
        ):
            self.char1.execute_cmd("redit 5")
        mock_load.assert_called_with("room", 5)
        mock_editor.assert_called()
        mock_editor.return_value.start.assert_called()
        assert self.char1.ndb.room_protos[5]["vnum"] == 5
        assert self.char1.ndb.current_vnum == 5

    def test_not_found_message(self):
        with patch("commands.redit.load_prototype", return_value=None):
            self.char1.msg.reset_mock()
            self.char1.execute_cmd("redit 99")
        out = self.char1.msg.call_args[0][0]
        assert "Room VNUM 99 not found" in out

    def test_load_existing_room(self):
        from evennia import create_object
        from typeclasses.rooms import Room

        room = create_object(Room, key="Existing", location=self.room1)
        room.db.room_id = 42
        room.db.desc = "Desc"
        room.db.area = "zone"
        dest = create_object(Room, key="dest", location=self.room1)
        dest.db.room_id = 43
        room.db.exits = {"north": dest}
        room.tags.add("dark", category="room_flag")

        with (
            patch("commands.redit.load_prototype", return_value=None),
            patch("commands.redit.OLCEditor") as mock_editor,
        ):
            self.char1.execute_cmd("redit 42")

        proto = self.char1.ndb.room_protos[42]
        assert proto["key"] == "Existing"
        assert proto["desc"] == "Desc"
        assert proto["exits"]["north"] == 43
        assert "dark" in proto["flags"]
        assert proto["area"] == "zone"
        mock_editor.assert_called()
