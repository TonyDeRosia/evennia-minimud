from unittest import mock, TestCase

from commands.building import CmdTeleport


class TestTeleportCommand(TestCase):
    """Ensure teleport looks up area by vnum when given digits."""

    def test_digits_use_find_area_by_vnum(self):
        caller = mock.Mock()
        caller.location = mock.Mock()

        cmd = CmdTeleport()
        cmd.caller = caller
        cmd.args = "42"
        cmd.msg = mock.Mock()

        with mock.patch("commands.building.find_area_by_vnum") as mock_lookup, \
             mock.patch("commands.building.ObjectDB.objects.filter", return_value=[]):
            cmd.func()
            mock_lookup.assert_called_with(42)
