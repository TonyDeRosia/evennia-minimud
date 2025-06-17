from unittest.mock import MagicMock, patch
from evennia.utils.test_resources import EvenniaTest
from commands.admin import BuilderCmdSet


class TestREditCommand(EvenniaTest):
    def setUp(self):
        from django.conf import settings

        settings.TEST_ENVIRONMENT = True
        super().setUp()
        self.char1.msg = MagicMock()
        self.char1.cmdset.add_default(BuilderCmdSet)

    def test_open_existing_proto(self):
        with (
            patch(
                "commands.redit.load_prototype", return_value={"vnum": 5}
            ) as mock_load,
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
        self.char1.msg.assert_called_with(
            "Room VNUM 99 not found. Use `redit create 99` to make a new room."
        )

    def test_malformed_proto_message(self):
        import json

        err = json.JSONDecodeError("bad", "", 0)
        with (
            patch("commands.redit.load_prototype", side_effect=err),
            patch("commands.redit.OLCEditor") as mock_editor,
        ):
            self.char1.msg.reset_mock()
            self.char1.execute_cmd("redit 200000")
            mock_editor.assert_not_called()
        self.char1.msg.assert_called_with(
            "Error loading prototype for room 200000. Try 'redit create 200000'."
        )

    def test_edit_live_room(self):
        from evennia.utils import create
        from typeclasses.rooms import Room

        room = create.create_object(
            Room,
            key="Old Room",
            location=self.char1.location,
            home=self.char1.location,
        )
        room.db.room_id = 5
        room.db.desc = "Old desc"
        room.db.area = "zone"
        room.tags.add("dark", category="room_flag")
        self.char1.location = room

        with (
            patch("commands.redit.load_prototype", return_value=None),
            patch("commands.redit.OLCEditor") as mock_editor,
            patch("commands.redit.ObjectDB.objects.filter", return_value=[room]),
        ):
            self.char1.execute_cmd("redit 5")
            mock_editor.assert_called()

        proto = self.char1.ndb.room_protos[5]
        assert proto["key"] == "Old Room"
        assert proto["desc"] == "Old desc"
        assert proto["flags"] == ["dark"]
        assert proto["area"] == "zone"

        proto["key"] = "New Room"
        proto["desc"] = "New desc"
        proto["flags"] = ["safe"]
        self.char1.ndb.room_protos[5] = proto

        with patch("commands.redit.save_prototype") as mock_save:
            from commands import redit

            redit.menunode_done(self.char1)
            mock_save.assert_called()

        assert room.key == "New Room"
        assert room.db.desc == "New desc"
        assert room.tags.has("safe", category="room_flag")
        assert not room.tags.has("dark", category="room_flag")

    def test_live_subcommand(self):
        from evennia.utils import create
        from typeclasses.rooms import Room

        room = create.create_object(
            Room,
            key="Live Room",
            location=self.char1.location,
            home=self.char1.location,
        )
        room.db.room_id = 7
        room.db.desc = "Live desc"
        room.db.area = "zone"
        room.tags.add("dark", category="room_flag")

        with (
            patch("commands.redit.load_prototype") as mock_load,
            patch("commands.redit.ObjectDB.objects.filter", return_value=[room]),
            patch("commands.redit.OLCEditor") as mock_editor,
        ):
            self.char1.execute_cmd("redit live 7")
            mock_load.assert_not_called()
            mock_editor.assert_called()

        proto = self.char1.ndb.room_protos[7]
        assert proto["key"] == "Live Room"
        assert proto["desc"] == "Live desc"
        assert proto["area"] == "zone"
        assert proto["flags"] == ["dark"]

    def test_live_not_found(self):
        with (
            patch("commands.redit.load_prototype") as mock_load,
            patch("commands.redit.ObjectDB.objects.filter", return_value=[]),
        ):
            self.char1.msg.reset_mock()
            self.char1.execute_cmd("redit live 99")
        mock_load.assert_not_called()
        self.char1.msg.assert_called_with("Room VNUM 99 not found.")

    def test_menu_missing_state(self):
        from commands import redit

        self.char1.ndb.room_protos = None
        self.char1.ndb.current_vnum = None
        self.char1.msg.reset_mock()

        result = redit.menunode_name(self.char1)
        assert result is None
        self.char1.msg.assert_called_with("Room editing state missing. Exiting.")

    def test_command_abort_clears_state(self):
        self.char1.ndb.room_protos = {5: {"vnum": 5}}
        self.char1.ndb.current_vnum = 5
        with patch("commands.redit.load_prototype", return_value=None):
            self.char1.execute_cmd("redit 99")
        assert self.char1.ndb.room_protos is None
        assert self.char1.ndb.current_vnum is None
