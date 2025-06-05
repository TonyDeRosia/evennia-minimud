from evennia.utils.test_resources import EvenniaTest
from world.system import stat_manager, state_manager
from world import stats


class TestStatManager(EvenniaTest):
    def setUp(self):
        super().setUp()
        stats.apply_stats(self.char1)

    def test_refresh_stats_race_class(self):
        char = self.char1
        char.db.race = "Elf"
        char.db.charclass = "Wizard"
        stat_manager.refresh_stats(char)
        self.assertEqual(char.traits.DEX.base, 7)
        self.assertEqual(char.traits.INT.base, 9)
        self.assertEqual(char.traits.STR.base, 4)
        self.assertEqual(char.traits.CON.base, 4)
        self.assertEqual(char.traits.WIS.base, 6)

    def test_effective_stat_with_temp_bonus(self):
        char = self.char1
        stat_manager.refresh_stats(char)
        base = char.traits.STR.value
        state_manager.add_temp_stat_bonus(char, "STR", 3, 1)
        self.assertEqual(stat_manager.get_effective_stat(char, "STR"), base + 3)

    def test_display_stat_block(self):
        char = self.char1
        stat_manager.refresh_stats(char)
        text = stat_manager.display_stat_block(char)
        self.assertIn("╔", text)
        self.assertIn("╚", text)
        self.assertIn("STR", text)
        self.assertIn("HP", text)

