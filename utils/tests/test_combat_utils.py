from unittest.mock import patch
from evennia.utils.test_resources import EvenniaTest
from world.system import stat_manager


class TestCombatCalculations(EvenniaTest):
    def test_check_hit_uses_accuracy_and_dodge(self):
        self.char1.db.stat_overrides = {"accuracy": 100}
        self.char2.db.stat_overrides = {"dodge": 0}
        stat_manager.refresh_stats(self.char1)
        stat_manager.refresh_stats(self.char2)
        with patch("world.system.stat_manager.randint", return_value=100):
            self.assertTrue(stat_manager.check_hit(self.char1, self.char2, base=50))
        self.char2.db.stat_overrides = {"dodge": 200}
        stat_manager.refresh_stats(self.char2)
        with patch("world.system.stat_manager.randint", return_value=1):
            self.assertFalse(stat_manager.check_hit(self.char1, self.char2, base=50))

    def test_roll_crit_respects_resist(self):
        self.char1.db.stat_overrides = {"crit_chance": 50}
        self.char2.db.stat_overrides = {"crit_resist": 20}
        stat_manager.refresh_stats(self.char1)
        stat_manager.refresh_stats(self.char2)
        with patch("world.system.stat_manager.randint", return_value=10):
            self.assertTrue(stat_manager.roll_crit(self.char1, self.char2))
        self.char2.db.stat_overrides = {"crit_resist": 60}
        stat_manager.refresh_stats(self.char2)
        with patch("world.system.stat_manager.randint", return_value=10):
            self.assertFalse(stat_manager.roll_crit(self.char1, self.char2))

    def test_roll_status_with_resist(self):
        self.char2.db.stat_overrides = {"status_resist": 50}
        stat_manager.refresh_stats(self.char2)
        with patch("world.system.stat_manager.randint", return_value=40):
            self.assertFalse(stat_manager.roll_status(self.char1, self.char2, 40))
        self.char2.db.stat_overrides = {"status_resist": 0}
        stat_manager.refresh_stats(self.char2)
        with patch("world.system.stat_manager.randint", return_value=40):
            self.assertTrue(stat_manager.roll_status(self.char1, self.char2, 40))

    def test_crit_damage_applies_bonus(self):
        self.char1.db.stat_overrides = {"crit_bonus": 50}
        stat_manager.refresh_stats(self.char1)
        self.assertEqual(stat_manager.crit_damage(self.char1, 10), 15)

