from unittest.mock import MagicMock, patch
from evennia.utils.test_resources import EvenniaTest

from utils.hit_chance import calculate_hit_success


class TestCalculateHitSuccess(EvenniaTest):
    def test_primary_proficiency(self):
        char = MagicMock()
        char.db = MagicMock(proficiencies={"cleave": 50})
        with patch("random.randint", return_value=50):
            self.assertTrue(calculate_hit_success(char, "cleave"))
        with patch("random.randint", return_value=51):
            self.assertFalse(calculate_hit_success(char, "cleave"))

    def test_support_skill_bonus(self):
        char = MagicMock()
        char.db = MagicMock(proficiencies={"fireball": 50, "spellcasting": 30})
        # total chance = 50 + 3 = 53
        with patch("random.randint", return_value=53):
            self.assertTrue(calculate_hit_success(char, "fireball", "spellcasting"))
        with patch("random.randint", return_value=54):
            self.assertFalse(calculate_hit_success(char, "fireball", "spellcasting"))

