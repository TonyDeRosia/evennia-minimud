import unittest
from unittest.mock import patch, MagicMock

from combat.round_manager import CombatRoundManager

class TestCombatRoundManagerCreate(unittest.TestCase):
    def setUp(self):
        CombatRoundManager._instance = None

    def test_round_time_zero_preserved(self):
        with patch('combat.engine.CombatEngine') as MockEngine, \
             patch('combat.round_manager.delay'):
            manager = CombatRoundManager.get()
            inst = manager.create_combat([], round_time=0)
        MockEngine.assert_called_with([], round_time=0)
        self.assertEqual(inst.round_time, 0)

if __name__ == '__main__':
    unittest.main()
