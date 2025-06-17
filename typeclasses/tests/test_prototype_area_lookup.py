"""Tests for commands relying on prototype-only areas."""

from unittest.mock import MagicMock, patch

from django.test import override_settings

from evennia.utils.test_resources import EvenniaTest

from commands.admin import BuilderCmdSet
from commands import aedit
from commands.areas import CmdRReg
from commands.building import CmdTeleport


@override_settings(DEFAULT_HOME=None)
class TestPrototypeAreaLookup(EvenniaTest):
    """Ensure commands fall back to prototypes for area information."""

    def setUp(self):
        super().setUp()
        self.char1.msg = MagicMock()
        self.char1.cmdset.add_default(BuilderCmdSet)

    @patch("world.areas._load_registry", return_value=([], []))
    @patch("world.areas.load_all_prototypes")
    @patch("commands.aedit.update_area")
    @patch("commands.aedit.save_prototype")
    @patch("commands.aedit.load_prototype")
    def test_aedit_add(self, mock_load_proto, mock_save, mock_update, mock_load_all, _):
        """`aedit add` works when only prototypes define the area."""

        mock_load_proto.return_value = {"vnum": 3}

        def _load(category):
            if category == "room":
                return {1: {"area": "zone", "room_id": 1}}
            if category == "npc":
                return {}
            return {}

        mock_load_all.side_effect = _load

        cmd = aedit.CmdAEdit()
        cmd.caller = self.char1
        cmd.session = self.char1.sessions.get()
        cmd.args = "add zone 3"
        cmd.func()

        mock_save.assert_called()
        mock_update.assert_called()
        self.assertIn("Room 3 added to zone.", self.char1.msg.call_args[0][0])

    @patch("world.areas._load_registry", return_value=([], []))
    @patch("world.areas.load_all_prototypes")
    def test_rreg(self, mock_load_all, _):
        """`rreg` succeeds when area exists only in prototypes."""

        def _load(category):
            if category == "room":
                return {3: {"area": "proto", "room_id": 3}}
            if category == "npc":
                return {}
            return {}

        mock_load_all.side_effect = _load

        cmd = CmdRReg()
        cmd.caller = self.char1
        cmd.args = "proto 3"
        cmd.func()

        self.assertEqual(self.char1.location.db.area, "proto")
        self.assertEqual(self.char1.location.db.room_id, 3)

    @patch("world.areas._load_registry", return_value=([], []))
    @patch("world.areas.load_all_prototypes")
    def test_tp(self, mock_load_all, _):
        """`tp` locates rooms when area info comes from prototypes."""

        def _load(category):
            if category == "room":
                return {2: {"area": "proto", "room_id": 2}}
            if category == "npc":
                return {}
            return {}

        mock_load_all.side_effect = _load

        # create a room matching the prototype
        start = self.char1.location
        self.char1.execute_cmd("dig north proto:2")
        target = start.db.exits.get("north")

        cmd = CmdTeleport()
        cmd.caller = self.char1
        cmd.args = "2"
        cmd.func()

        self.assertEqual(self.char1.location, target)

    @patch("world.areas._load_registry", return_value=([], []))
    @patch("world.areas.load_all_prototypes")
    def test_rlist(self, mock_load_all, _):
        """`rlist` lists prototypes when no rooms exist."""

        def _load(category):
            if category == "room":
                return {
                    1: {"area": "proto", "room_id": 1},
                    2: {"area": "proto", "room_id": 2},
                }
            if category == "npc":
                return {}
            return {}

        mock_load_all.side_effect = _load

        self.char1.msg.reset_mock()
        self.char1.execute_cmd("rlist proto")
        out = self.char1.msg.call_args[0][0]
        self.assertIn("Rooms in proto", out)
        self.assertIn("1:", out)
        self.assertIn("2:", out)
        self.assertIn("(unbuilt)", out)

