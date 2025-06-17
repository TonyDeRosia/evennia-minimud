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
            patch(
                "commands.redit.ObjectDB.objects.filter", return_value=[room]
            ),
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

    def test_summary_from_live_room_proto(self):
        from evennia.utils import create
        from typeclasses.rooms import Room
        from commands import redit

        room = create.create_object(
            Room,
            key="Summ Room",
            location=self.char1.location,
            home=self.char1.location,
        )
        room.db.room_id = 8
        room.db.desc = "Sum desc"

        proto = redit.proto_from_room(room)
        self.char1.ndb.room_protos = {8: proto}
        self.char1.ndb.current_vnum = 8
        out = redit._summary(self.char1)
        assert "Editing room 8" in out

    def test_edit_live_room_message(self):
        from evennia.utils import create
        from typeclasses.rooms import Room

        room = create.create_object(
            Room,
            key="Test Room",
            location=self.char1.location,
            home=self.char1.location,
        )
        room.db.room_id = 6

        with (
            patch("commands.redit.load_prototype", return_value=None),
            patch("commands.redit.OLCEditor"),
            patch("commands.redit.ObjectDB.objects.filter", return_value=[room]),
        ):
            self.char1.msg.reset_mock()
            self.char1.execute_cmd("redit 6")

        self.char1.msg.assert_called_with(
            "Editing live room #6 (no prototype found)."
        )

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
            patch(
                "commands.redit.ObjectDB.objects.filter", return_value=[room]
            ),
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
        self.char1.msg.assert_called_with(
            "Room editing state missing. Exiting."
        )

    def test_command_abort_clears_state(self):
        self.char1.ndb.room_protos = {5: {"vnum": 5}}
        self.char1.ndb.current_vnum = 5
        with patch("commands.redit.load_prototype", return_value=None):
            self.char1.execute_cmd("redit 99")
        assert self.char1.ndb.room_protos is None
        assert self.char1.ndb.current_vnum is None

    def test_redit_here_saves_room(self):
        """Editing the current room should update live object and prototype."""
        from evennia.utils import create
        from typeclasses.rooms import Room
        from commands import redit

        room = create.create_object(
            Room,
            key="Start Room",
            location=self.char1.location,
            home=self.char1.location,
        )
        room.db.desc = "Old desc"
        self.char1.location = room
        vnum = 200001

        with (
            patch("commands.redit.validate_vnum", return_value=True),
            patch("commands.redit.register_vnum"),
            patch("commands.redit.save_prototype") as mock_save,
            patch("commands.redit.OLCEditor") as mock_editor,
        ):
            self.char1.execute_cmd(f"redit here {vnum}")
            mock_editor.assert_called()

        proto = self.char1.ndb.room_protos[vnum]
        assert proto["key"] == "Start Room"
        assert proto["desc"] == "Old desc"

        proto["key"] = "New Room"
        proto["desc"] = "New desc"
        self.char1.ndb.room_protos[vnum] = proto

        with (
            patch("commands.redit.save_prototype") as mock_save,
            patch(
                "commands.redit.ObjectDB.objects.filter",
                return_value=[room],
            ),
        ):
            redit.menunode_done(self.char1)
            mock_save.assert_called()
            saved = mock_save.call_args[0][1]
            assert saved["key"] == "New Room"
            assert saved["desc"] == "New desc"

        assert room.key == "New Room"
        assert room.db.desc == "New desc"

    def test_save_live_room_no_area_error(self):
        """Saving a live room with no area should show an error instead of crashing."""
        from evennia.utils import create
        from typeclasses.rooms import Room
        from commands import redit

        room = create.create_object(
            Room,
            key="Lonely Room",
            location=self.char1.location,
            home=self.char1.location,
        )
        room.db.room_id = 9
        # no area assigned
        self.char1.location = room

        with (
            patch("commands.redit.load_prototype", return_value=None),
            patch("commands.redit.OLCEditor") as mock_editor,
            patch("commands.redit.ObjectDB.objects.filter", return_value=[room]),
        ):
            self.char1.execute_cmd("redit 9")
            mock_editor.assert_called()

        proto = self.char1.ndb.room_protos[9]
        assert "area" not in proto

        self.char1.msg.reset_mock()
        with (
            patch("commands.redit.save_prototype") as mock_save,
            patch("commands.redit.ObjectDB.objects.filter", return_value=[room]),
        ):
            redit.menunode_done(self.char1)
            mock_save.assert_not_called()

        self.char1.msg.assert_called_with(
            "Error: This room has no area assigned. Cannot save prototype."
        )
