import unittest
from combat.combat_utils import highlight_keywords

class TestHighlightKeywords(unittest.TestCase):
    def test_colors_misses_when_plain(self):
        result = highlight_keywords("Alice misses Bob")
        self.assertIn("|Cmisses|n", result)

    def test_skips_when_already_colored(self):
        text = "Alice |Cmisses|n Bob"
        self.assertEqual(highlight_keywords(text), text)

if __name__ == "__main__":
    unittest.main()
