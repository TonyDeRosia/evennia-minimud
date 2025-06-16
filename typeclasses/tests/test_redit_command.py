from unittest.mock import MagicMock, patch
from evennia.utils.test_resources import EvenniaTest
from commands.admin import BuilderCmdSet


class TestREditCommand(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.char1.msg = MagicMock()
        self.char1.cmdset.add_default(BuilderCmdSet)

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
        self.char1.msg.assert_called_with(
            "Room VNUM 99 not found. Use `redit create 99` to make a new room."
        )
