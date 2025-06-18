from unittest.mock import MagicMock
from evennia.utils import create
from evennia.utils.test_resources import EvenniaTest
from commands.spells import CmdLearnSpell

class TestSpellLearning(EvenniaTest):
    def test_learn_consumes_practice(self):
        trainer = create.create_object("typeclasses.objects.Object", key="trainer", location=self.room1)
        trainer.db.spell_training = "fireball"
        self.char1.location = trainer.location
        self.char1.db.practice_sessions = 1
        cmd = CmdLearnSpell()
        cmd.caller = self.char1
        cmd.obj = trainer
        cmd.args = ""
        cmd.msg = MagicMock()
        cmd.func()
        spells = self.char1.db.spells
        self.assertEqual(len(spells), 1)
        self.assertEqual(spells[0].key, "fireball")
        self.assertEqual(self.char1.db.proficiencies.get("fireball"), 25)
        self.assertEqual(self.char1.db.practice_sessions, 0)
