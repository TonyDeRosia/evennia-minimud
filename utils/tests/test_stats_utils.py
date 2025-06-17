from evennia.utils.test_resources import EvenniaTest
from utils.stats_utils import get_display_scroll


class TestDisplayScroll(EvenniaTest):
    def test_sated_display(self):
        char = self.char1
        char.db.sated = 0
        sheet = get_display_scroll(char)
        self.assertIn("Sated", sheet)
        self.assertIn("URGENT", sheet)

    def test_bonus_display(self):
        char = self.char1
        char.db.equip_bonuses = {"STR": 2}
        sheet = get_display_scroll(char)
        self.assertIn("(+2)", sheet)

    def test_sated_display_full(self):
        char = self.char1
        char.db.sated = 150
        sheet = get_display_scroll(char)
        self.assertIn("Sated", sheet)
        self.assertIn("100", sheet)

    def test_sated_hidden_at_max_level(self):
        char = self.char1
        char.db.level = 100
        char.db.sated = 50
        sheet = get_display_scroll(char)
        self.assertNotIn("Sated", sheet)

    def test_practice_and_training_display(self):
        char = self.char1
        char.db.practice_sessions = 2
        char.db.training_points = 1
        sheet = get_display_scroll(char)
        self.assertIn("Prac 2", sheet)
        self.assertIn("TP 1", sheet)

    def test_practice_and_training_labels_present(self):
        char = self.char1
        char.db.practice_sessions = 3
        char.db.training_points = 5
        sheet = get_display_scroll(char)
        self.assertIn("Prac", sheet)
        self.assertIn("TP", sheet)

    def test_xp_and_tnl_display(self):
        char = self.char1
        char.db.experience = 10
        char.db.tnl = 90
        sheet = get_display_scroll(char)
        self.assertIn("XP|n 10", sheet)
        self.assertIn("TNL|n 90", sheet)
    def test_tick_updates_display(self):
        from world.system import state_manager

        char = self.char1
        char.db.sated = 10

        state_manager.tick_character(char)

        sheet = get_display_scroll(char)
        self.assertIn("|ySated|n", sheet)
        self.assertIn("9", sheet)

    def test_haste_stat_displayed(self):
        sheet = get_display_scroll(self.char1)
        self.assertIn("Haste", sheet)

    def test_race_and_class_displayed(self):
        char = self.char1
        char.db.race = "Orc"
        char.db.charclass = "Warrior"
        sheet = get_display_scroll(char)
        self.assertIn("|cRace:|n Orc", sheet)
        self.assertIn("|cClass:|n Warrior", sheet)


