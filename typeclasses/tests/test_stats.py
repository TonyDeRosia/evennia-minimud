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
