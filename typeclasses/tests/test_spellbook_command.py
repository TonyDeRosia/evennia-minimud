from unittest.mock import MagicMock
from evennia.utils.test_resources import EvenniaTest
from commands.spells import CmdSpellbook
from combat.spells import Spell

class TestSpellbook(EvenniaTest):
    def setUp(self):
        super().setUp()
        # give char1 a known spell
        self.char1.db.spells = [Spell("fireball", "INT", 10, "A fiery blast.")]
        self.char1.msg = MagicMock()

    def test_spellbook_lists_spells(self):
        self.char1.execute_cmd("spells")
        out = self.char1.msg.call_args[0][0]
        self.assertIn("fireball", out)

    def test_spellbook_specific_spell(self):
        self.char1.msg = MagicMock()
        self.char1.execute_cmd("spells fireball")
        out = self.char1.msg.call_args[0][0]
        self.assertIn("Fireball", out)
        self.assertIn("Mana Cost", out)
        self.assertIn("Proficiency", out)
        self.assertIn("A fiery blast.", out)

    def test_spellbook_unknown_spell(self):
        self.char1.msg = MagicMock()
        self.char1.execute_cmd("spells unknown")
        out = self.char1.msg.call_args[0][0]
        self.assertIn("not learned", out.lower())
