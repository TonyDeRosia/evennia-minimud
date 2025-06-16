import unittest
from itertools import cycle
from unittest.mock import patch

from combat.actions.utils import check_hit


class Dummy:
    def __init__(self, key="dummy"):
        self.key = key


class TestAutoAttackAccuracy(unittest.TestCase):
    def test_auto_attack_hit_rate(self):
        attacker = Dummy("attacker")
        defender = Dummy("defender")

        hit_rng = cycle(range(1, 101))
        evade_rng = cycle(range(1, 101))

        def rand_hit(*args, **kwargs):
            return next(hit_rng)

        def rand_evade(*args, **kwargs):
            return next(evade_rng)

        def get_stat(obj, stat):
            if obj is attacker and stat == "accuracy":
                return 12
            return 0

        hits = 0
        trials = 100
        with patch("world.system.stat_manager.randint", side_effect=rand_hit), \
             patch("combat.combat_utils.random.randint", side_effect=rand_evade), \
             patch("world.system.stat_manager.get_effective_stat", side_effect=get_stat), \
             patch("world.system.state_manager.get_effective_stat", side_effect=get_stat):
            for _ in range(trials):
                success, _ = check_hit(attacker, defender)
                if success:
                    hits += 1

        rate = hits / trials
        self.assertGreaterEqual(rate, 0.70)
        self.assertLessEqual(rate, 0.80)


if __name__ == "__main__":
    unittest.main()
