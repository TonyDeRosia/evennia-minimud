import os
import unittest
import django
import evennia

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()
if getattr(evennia, "SESSION_HANDLER", None) is None:
    evennia._init()

from combat.ai_combat import _iter_abilities


class DummyKey:
    def __init__(self, key):
        self.key = key


class DummyName:
    def __init__(self, name):
        self.name = name


class TestIterAbilities(unittest.TestCase):
    def test_list_string_percent(self):
        data = ["fireball(30%)", "ice"]
        result = list(_iter_abilities(data))
        self.assertEqual(result, [("fireball", 30), ("ice", 100)])

    def test_dict_mapping(self):
        data = {"slash": 50, "bash": 75}
        result = list(_iter_abilities(data))
        self.assertIn(("slash", 50), result)
        self.assertIn(("bash", 75), result)

    def test_single_string(self):
        result = list(_iter_abilities("shock"))
        self.assertEqual(result, [("shock", 100)])

    def test_object_with_key(self):
        obj = DummyKey("heal")
        result = list(_iter_abilities(obj))
        self.assertEqual(result, [("heal", 100)])

    def test_object_with_name(self):
        obj = DummyName("cure")
        result = list(_iter_abilities(obj))
        self.assertEqual(result, [("cure", 100)])


if __name__ == "__main__":
    unittest.main()
