import unittest
from unittest.mock import MagicMock
from django.test import override_settings
from combat.round_manager import CombatInstance


class TestCombatTickLogging(unittest.TestCase):
    @override_settings(COMBAT_DEBUG_TICKS=True)
    def test_tick_emits_debug_log(self):
        fighter1 = object()
        fighter2 = object()
        engine = MagicMock()
        engine.participants = []
        inst = CombatInstance(1, engine, {fighter1, fighter2})
        inst.sync_participants = MagicMock()
        inst.has_active_fighters = MagicMock(return_value=True)
        inst.process_round = MagicMock()
        with self.assertLogs('combat.round_manager', level='DEBUG') as cm:
            inst._tick()
        self.assertTrue(any('Combat tick' in msg for msg in cm.output))
