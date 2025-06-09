from evennia.utils.test_resources import EvenniaTest

class TestResistanceMatrix(EvenniaTest):
    def test_fire_resistance(self):
        from combat.damage_types import DamageType, ResistanceType, get_damage_multiplier
        mult = get_damage_multiplier([ResistanceType.FIRE], DamageType.FIRE)
        self.assertEqual(mult, 0.5)

    def test_shadow_weak_to_holy(self):
        from combat.damage_types import DamageType, ResistanceType, get_damage_multiplier
        mult = get_damage_multiplier([ResistanceType.SHADOW], DamageType.HOLY)
        self.assertEqual(mult, 1.5)
