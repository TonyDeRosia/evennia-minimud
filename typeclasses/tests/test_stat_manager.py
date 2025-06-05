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

    def test_derived_stats_increase_with_primary(self):
        char = self.char1
        stat_manager.refresh_stats(char)

        base_attack = char.db.derived_stats.get("attack_power")
        char.traits.STR.base += 5
        stat_manager.refresh_stats(char)
        self.assertGreater(char.db.derived_stats.get("attack_power"), base_attack)

        base_regen = char.db.derived_stats.get("mana_regen")
        char.traits.WIS.base += 3
        stat_manager.refresh_stats(char)
        self.assertGreater(char.db.derived_stats.get("mana_regen"), base_regen)

        base_stealth = char.db.derived_stats.get("stealth")
        char.traits.DEX.base += 2
        stat_manager.refresh_stats(char)
        self.assertGreater(char.db.derived_stats.get("stealth"), base_stealth)

    def test_refresh_stats_handles_missing_base_stats(self):
        char = self.char1
        char.db.base_primary_stats = None
        stat_manager.refresh_stats(char)
        self.assertIsInstance(char.db.base_primary_stats, dict)
        for key in stats.CORE_STAT_KEYS:
            self.assertIn(key, char.db.base_primary_stats)

    def test_active_effect_modifiers(self):
        char = self.char1
        stat_manager.refresh_stats(char)
        base = char.traits.STR.base
        state_manager.add_effect(char, "STR", 2)
        self.assertEqual(char.traits.STR.base, base + 5)
        self.assertEqual(stat_manager.get_effective_stat(char, "STR"), base + 5)
        state_manager.tick_character(char)
        state_manager.tick_character(char)
        self.assertEqual(char.traits.STR.base, base)

    def test_debuff_modifiers(self):
        char = self.char1
        stat_manager.refresh_stats(char)
        base = char.traits.DEX.base
        state_manager.add_effect(char, "stunned", 1)
        self.assertEqual(char.traits.DEX.base, base - 5)
        state_manager.tick_character(char)
        self.assertEqual(char.traits.DEX.base, base)
