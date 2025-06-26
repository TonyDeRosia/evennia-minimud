import unittest
from combat.combatants import _current_hp

class Dummy:
    pass

class HPDummy:
    def __init__(self, hp):
        self.hp = hp

class TraitDummy:
    class Traits:
        def __init__(self, current):
            self.health = type('H', (), {'current': current})()
    def __init__(self, current):
        self.traits = self.Traits(current)

class TestCurrentHP(unittest.TestCase):
    def test_no_hp_or_trait_returns_zero(self):
        self.assertEqual(_current_hp(Dummy()), 0)

    def test_hp_attribute_parsed_as_int(self):
        self.assertEqual(_current_hp(HPDummy(5)), 5)

    def test_invalid_hp_returns_zero(self):
        obj = HPDummy("bad")
        self.assertEqual(_current_hp(obj), 0)

    def test_health_trait_used(self):
        self.assertEqual(_current_hp(TraitDummy(7)), 7)

    def test_invalid_trait_returns_zero(self):
        obj = TraitDummy("bad")
        self.assertEqual(_current_hp(obj), 0)

if __name__ == "__main__":
    unittest.main()
