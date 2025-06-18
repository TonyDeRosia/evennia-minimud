import unittest

from world.constants import CLASS_LIST
from world.system.class_skills import CLASS_SKILLS


class TestClassSkills(unittest.TestCase):
    def test_all_classes_have_basic_skills(self):
        for cls in CLASS_LIST:
            class_name = cls["name"]
            level1 = CLASS_SKILLS[class_name][1]
            self.assertIn("kick", level1)
            self.assertIn("recall", level1)
