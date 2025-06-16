import unittest

from world.constants import CLASS_LIST
from world.system.class_skills import CLASS_SKILLS


class TestClassSkills(unittest.TestCase):
    def test_all_classes_have_kick_skill(self):
        for cls in CLASS_LIST:
            class_name = cls["name"]
            self.assertIn("kick", CLASS_SKILLS[class_name][1])
