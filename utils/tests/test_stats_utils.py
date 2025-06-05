from evennia.utils.test_resources import EvenniaTest
from utils.stats_utils import get_display_scroll


class TestDisplayScroll(EvenniaTest):
    def test_sated_display(self):
        char = self.char1
        char.db.sated = 0
        sheet = get_display_scroll(char)
        self.assertIn("Sated", sheet)
        self.assertIn("URGENT", sheet)
