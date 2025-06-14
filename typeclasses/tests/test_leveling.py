from unittest.mock import MagicMock
from evennia.utils.test_resources import EvenniaTest
from django.test import override_settings
from django.conf import settings
from world.system import state_manager


class TestLeveling(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.char1.db.exp = 0
        self.char1.db.level = 1
        self.char1.db.practice_sessions = 0
        self.char1.db.training_points = 0
        self.char1.msg = MagicMock()

    def test_single_level_up_awards_resources(self):
        self.char1.db.exp = 100
        state_manager.check_level_up(self.char1)
        self.assertEqual(self.char1.db.level, 2)
        self.assertEqual(self.char1.db.practice_sessions, 3)
        self.assertEqual(self.char1.db.training_points, 1)
        self.char1.msg.assert_called()
        output = self.char1.msg.call_args[0][0]
        self.assertIn("practice sessions", output)
        self.assertIn("training session", output)

    def test_multiple_level_ups(self):
        self.char1.db.exp = 210
        state_manager.check_level_up(self.char1)
        self.assertEqual(self.char1.db.level, 3)
        self.assertEqual(self.char1.db.practice_sessions, 6)
        self.assertEqual(self.char1.db.training_points, 2)
        output = self.char1.msg.call_args[0][0]
        self.assertIn("practice sessions", output)
        self.assertIn("training session", output)


class TestExperienceCarryOver(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.char1.db.level = 1
        self.char1.db.experience = 0
        self.char1.db.tnl = settings.XP_PER_LEVEL
        self.char1.msg = MagicMock()

    @override_settings(XP_CARRY_OVER=False)
    def test_no_carry_over_discards_excess(self):
        state_manager.gain_xp(self.char1, settings.XP_PER_LEVEL + 10)
        self.assertEqual(self.char1.db.level, 2)
        self.assertEqual(self.char1.db.experience, settings.XP_PER_LEVEL)
        self.assertEqual(self.char1.db.tnl, settings.XP_PER_LEVEL)

    @override_settings(XP_CARRY_OVER=True)
    def test_carry_over_keeps_excess(self):
        state_manager.gain_xp(self.char1, settings.XP_PER_LEVEL + 10)
        self.assertEqual(self.char1.db.level, 2)
        self.assertEqual(
            self.char1.db.experience, settings.XP_PER_LEVEL + 10
        )
        self.assertEqual(self.char1.db.tnl, settings.XP_PER_LEVEL - 10)


class TestGainXpAndLevelUp(EvenniaTest):
    """Tests for gain_xp and level_up helpers."""

    def setUp(self):
        super().setUp()
        self.char1.db.level = 1
        self.char1.db.experience = 0
        self.char1.db.tnl = settings.XP_PER_LEVEL
        self.char1.db.practice_sessions = 0
        self.char1.db.training_points = 0
        self.char1.msg = MagicMock()

    def test_gain_xp_lowers_tnl(self):
        state_manager.gain_xp(self.char1, 5)
        self.assertEqual(self.char1.db.tnl, settings.XP_PER_LEVEL - 5)

    def test_gain_xp_levels_when_tnl_zero(self):
        state_manager.gain_xp(self.char1, settings.XP_PER_LEVEL)
        self.assertEqual(self.char1.db.level, 2)
        self.assertEqual(self.char1.db.practice_sessions, 3)
        self.assertEqual(self.char1.db.training_points, 1)
        self.assertEqual(self.char1.db.tnl, settings.XP_PER_LEVEL)

    def test_level_up_awards_resources(self):
        state_manager.level_up(self.char1)
        self.assertEqual(self.char1.db.level, 2)
        self.assertEqual(self.char1.db.practice_sessions, 3)
        self.assertEqual(self.char1.db.training_points, 1)
        self.assertEqual(self.char1.db.tnl, settings.XP_PER_LEVEL)
