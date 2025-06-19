from evennia.utils.test_resources import EvenniaTest
from world.system import state_manager


class TestXpScaling(EvenniaTest):
    def test_calculate_xp_reward(self):
        base = 10
        cases = [
            (1, 4, 1.5),
            (1, 3, 1.25),
            (1, 2, 1.1),
            (1, 1, 1.0),
            (2, 1, 0.8),
            (3, 1, 0.5),
            (4, 1, 0.0),
        ]

        for atk_level, npc_level, mult in cases:
            self.char1.db.level = atk_level
            self.char2.db.level = npc_level
            result = state_manager.calculate_xp_reward(self.char1, self.char2, base)
            expected = max(0, int(round(base * mult)))
            self.assertEqual(result, expected)

