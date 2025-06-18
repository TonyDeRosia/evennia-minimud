import unittest
from combat.ai_combat import _iter_abilities


class TestIterAbilities(unittest.TestCase):
    def test_from_list(self):
        data = ["fireball(25%)"]
        self.assertEqual(list(_iter_abilities(data)), [("fireball", 25)])

    def test_from_dict(self):
        data = {"fireball(25%)": 100}
        self.assertEqual(list(_iter_abilities(data)), [("fireball", 25)])

    def test_from_string(self):
        self.assertEqual(list(_iter_abilities("fireball(25%)")), [("fireball", 25)])


