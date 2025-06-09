from unittest.mock import MagicMock
from evennia.utils.test_resources import EvenniaTest
from world import stats


class TestStats(EvenniaTest):
    """Tests for the stats module."""

    def test_apply_stats_idempotent(self):
        char = self.char1
        # apply stats once
        stats.apply_stats(char)
        initial = {key: char.traits.get(key).base for key in stats.CORE_STAT_KEYS}
        # apply again - should not change values
        stats.apply_stats(char)
        again = {key: char.traits.get(key).base for key in stats.CORE_STAT_KEYS}
        self.assertEqual(initial, again)

    def test_perception_default(self):
        char = self.char1
        stats.apply_stats(char)
        self.assertEqual(char.traits.perception.base, 5)

    def test_sum_bonus_fallback_attributes(self):
        """sum_bonus should read from attributes if obj.db is unusable."""
        char = self.char1
        stats.apply_stats(char)

        class Dummy:
            pass

        dummy = Dummy()
        dummy.traits = char.traits
        dummy.attributes = char.attributes
        dummy.db = None

        char.attributes.add("stealth_bonus", 7)
        self.assertEqual(stats.sum_bonus(dummy, "stealth"), char.traits.stealth.value + 7)

    def test_secondary_stats_follow_core(self):
        char = self.char1
        stats.apply_stats(char)

        # dodge depends on DEX
        initial_dodge = stats.sum_bonus(char, "dodge")
        char.traits.DEX.base += 5
        self.assertGreater(stats.sum_bonus(char, "dodge"), initial_dodge)

        # block_rate depends on STR
        initial_block = stats.sum_bonus(char, "block_rate")
        char.traits.STR.base += 5
        self.assertGreater(stats.sum_bonus(char, "block_rate"), initial_block)

    def test_stealth_fails_against_high_detection(self):
        attacker = self.char1
        target = self.char2
        stats.apply_stats(attacker)
        stats.apply_stats(target)
        attacker.traits.stealth.base = 5
        target.traits.detection.base = 10
        attacker.db.is_stealthed = True
        attacker.msg = MagicMock()
        target.msg = MagicMock()

        failed = stats.check_stealth_detection(attacker, target)

        self.assertTrue(failed)
        self.assertFalse(attacker.db.is_stealthed)
        attacker.msg.assert_called()
        target.msg.assert_called()
