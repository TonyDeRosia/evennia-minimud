from evennia.utils.test_resources import EvenniaTest

from utils.defense_scaling import DefensiveStats


class TestDefensiveStats(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.ds = DefensiveStats()

    def test_zero_effectiveness(self):
        self.assertEqual(self.ds.armor_effectiveness(0), 0)

    def test_hundred_stat_half_effective(self):
        self.assertAlmostEqual(self.ds.dodge_effectiveness(100), 50.0, places=1)

    def test_required_stat_inverse(self):
        eff = self.ds.parry_effectiveness(150) / 100
        self.assertAlmostEqual(self.ds.stat_for_effectiveness(eff, "parry"), 150, places=1)

    def test_negative_value_raises(self):
        with self.assertRaises(ValueError):
            self.ds.block_effectiveness(-5)


