import unittest
from unittest.mock import MagicMock

from combat.damage_processor import DamageProcessor

class TestDamageProcessorBroadcast(unittest.TestCase):
    def test_no_participants_returns_early(self):
        engine = MagicMock()
        manager = MagicMock()
        manager.participants = []
        processor = DamageProcessor(engine, manager, MagicMock())
        processor.round_output = ["msg"]
        room = MagicMock()
        processor._broadcast_round_output(room)
        room.msg_contents.assert_not_called()

if __name__ == "__main__":
    unittest.main()
