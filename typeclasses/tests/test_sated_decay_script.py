from django.test import override_settings
from evennia.utils.test_resources import EvenniaTest
from scripts.sated_decay import SatedDecayScript


@override_settings(DEFAULT_HOME=None)
class TestSatedDecayScript(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.script = SatedDecayScript()
        self.script.at_script_creation()

    def test_hunger_tick_reduces_sated(self):
        char = self.char1
        char.db.sated = 2
        self.script.at_repeat()
        self.assertEqual(char.db.sated, 1)

    def test_hungry_effect_applied_at_zero(self):
        char = self.char1
        char.db.sated = 1
        self.script.at_repeat()
        self.assertEqual(char.db.sated, 0)
        self.assertTrue(char.tags.has("hungry_thirsty", category="status"))
