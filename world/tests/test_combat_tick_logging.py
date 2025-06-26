import unittest
from unittest.mock import MagicMock, patch
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

    @override_settings(COMBAT_DEBUG_TICKS=True)
    def test_schedule_emits_debug_log(self):
        fighter1 = object()
        fighter2 = object()
        engine = MagicMock()
        engine.participants = []
        inst = CombatInstance(1, engine, {fighter1, fighter2})
        with patch('combat.round_manager.delay') as mock_delay:
            mock_delay.return_value = MagicMock()
            with self.assertLogs('combat.round_manager', level='DEBUG') as cm:
                inst._schedule_tick()
        self.assertTrue(any('Scheduling combat tick' in msg for msg in cm.output))

    def test_zero_round_time_skips_schedule(self):
        engine = MagicMock()
        engine.participants = []
        inst = CombatInstance(1, engine, {object(), object()}, round_time=0)
        with patch('combat.round_manager.delay') as mock_delay:
            inst._schedule_tick()
        mock_delay.assert_not_called()
        self.assertIsNone(inst.tick_handle)

    def test_negative_round_time_skips_schedule(self):
        engine = MagicMock()
        engine.participants = []
        inst = CombatInstance(1, engine, {object(), object()}, round_time=-1)
        with patch('combat.round_manager.delay') as mock_delay:
            inst._schedule_tick()
        mock_delay.assert_not_called()
        self.assertIsNone(inst.tick_handle)
