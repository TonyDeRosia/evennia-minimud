from evennia.utils.test_resources import EvenniaTest
from commands.admin import parse_stat_mods


class TestParseStatMods(EvenniaTest):
    def test_alias_and_lowercase(self):
        mods, desc = parse_stat_mods("armor_pen+5, crit_chance+3 test")
        self.assertEqual(mods, {"piercing": 5, "crit_chance": 3})
        self.assertEqual(desc, "test")

    def test_invalid_mod_format(self):
        with self.assertRaises(ValueError):
            parse_stat_mods("hp+g")
        with self.assertRaises(ValueError):
            parse_stat_mods("critchance++5")

    def test_underscore_names(self):
        mods, _ = parse_stat_mods("critical_chance+2")
        self.assertEqual(mods, {"crit_chance": 2})

    def test_negative_modifier(self):
        mods, _ = parse_stat_mods("accuracy-3")
        self.assertEqual(mods, {"accuracy": -3})
