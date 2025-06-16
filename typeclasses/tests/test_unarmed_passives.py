from evennia.utils.test_resources import EvenniaTest
from django.test import override_settings
from commands.update import UpdateCmdSet
from world.system import state_manager
from world.system.class_skills import MELEE_CLASSES

@override_settings(DEFAULT_HOME=None)
class TestUnarmedPassives(EvenniaTest):
    def test_unarmed_auto_granted(self):
        self.assertIn("Unarmed", self.char1.db.skills)
        self.assertEqual(self.char1.db.proficiencies.get("Unarmed"), 25)

    def test_update_grants_hand_to_hand(self):
        self.char1.cmdset.add_default(UpdateCmdSet)
        self.char2.db.charclass = next(iter(MELEE_CLASSES))
        self.char2.db.level = 1
        self.char1.execute_cmd(f"update {self.char2.key}")
        self.assertIn("Hand-to-Hand", self.char2.db.skills)
        self.assertEqual(self.char2.db.proficiencies.get("Hand-to-Hand"), 25)
