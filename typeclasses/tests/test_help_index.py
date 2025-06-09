from unittest.mock import MagicMock
from evennia.utils.test_resources import EvenniaTest
from django.test import override_settings
from evennia.utils.ansi import strip_ansi

@override_settings(DEFAULT_HOME=None)
class TestHelpIndexOrdering(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.char1.msg = MagicMock()

    def test_help_index_sorted(self):
        self.char1.execute_cmd('help')
        out = strip_ansi(self.char1.msg.call_args[0][0])
        entries = []
        for line in out.splitlines():
            line = line.strip()
            if not line or line.startswith('--') or line.startswith('Commands') or line.startswith('Game'):
                continue
            entries.extend(line.split())
        self.assertEqual(entries, sorted(entries, key=str.lower))

