import unittest
from unittest.mock import MagicMock, patch

from combat.aggro_tracker import AggroTracker


class TestAggroTracker(unittest.TestCase):
    def test_award_experience_removes_victim(self):
        tracker = AggroTracker()
        attacker = MagicMock(pk=1)
        victim = MagicMock(pk=2)
        active = [attacker]

        with patch("combat.aggro_tracker.state_manager.get_effective_stat", return_value=0), \
             patch("combat.aggro_tracker.state_manager.calculate_xp_reward", return_value=5), \
             patch("combat.aggro_tracker.award_xp"):
            tracker.track(victim, attacker)
            assert victim in tracker.table
            tracker.award_experience(attacker, victim, active)

        assert victim not in tracker.table


if __name__ == "__main__":
    unittest.main()
