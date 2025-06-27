import unittest
from unittest.mock import MagicMock, patch
from combat.round_manager import CombatInstance


class TestCombatEndInvalidInstance(unittest.TestCase):
    def test_room_message_skipped_on_invalid_instance(self):
        engine = MagicMock()
        engine.participants = []
        inst = CombatInstance(1, engine, set())
        inst.sync_participants = MagicMock()
        inst.room = MagicMock()
        with (
            patch('combat.round_manager.CombatRoundManager.get') as mock_get,
            patch('combat.round_manager.log_info') as mock_info,
            patch('combat.round_manager.log_trace') as mock_trace,
        ):
            mock_get.return_value = MagicMock(remove_combat=MagicMock())
            inst.end_combat("Invalid combat instance")
        inst.room.msg_contents.assert_not_called()
        mock_info.assert_called_with("Invalid combat instance")
        mock_trace.assert_not_called()

