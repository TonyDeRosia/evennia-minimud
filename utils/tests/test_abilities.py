from evennia.utils.test_resources import EvenniaTest
from world.abilities import colorize_name


class TestColorizeName(EvenniaTest):
    def test_colorize_fireball(self):
        self.assertEqual(colorize_name("Fireball"), "|cFireball|n")
