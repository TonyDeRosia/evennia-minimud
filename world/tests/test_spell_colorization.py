from evennia.utils.test_resources import EvenniaTest
from world.spells import colorize_spell

class TestSpellColor(EvenniaTest):
    def test_fire_spell_color(self):
        colored = colorize_spell("fireball")
        assert colored.startswith("|r") and colored.endswith("|n")

    def test_heal_spell_color(self):
        colored = colorize_spell("heal")
        assert colored.startswith("|w") and colored.endswith("|n")

