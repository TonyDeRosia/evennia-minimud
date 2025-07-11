import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")

import django
import evennia
import unittest
from unittest.mock import patch, MagicMock

django.setup()
if getattr(evennia, "SESSION_HANDLER", None) is None:
    evennia._init()

from combat.damage_types import DamageType
from combat.body_parts import HitLocation


class TestActionUtils(unittest.TestCase):
    def setUp(self):
        self.attacker = MagicMock(key="Attacker")
        self.target = MagicMock(key="Target")

    def test_check_hit_miss(self):
        from combat.engine import CombatMath
        with patch("combat.engine.combat_math.stat_manager.check_hit", return_value=False):
            hit, msg = CombatMath.check_hit(self.attacker, self.target)
        self.assertFalse(hit)
        self.assertIn("misses", msg)

    def test_check_hit_parry(self):
        from combat.engine import CombatMath
        with patch("combat.engine.combat_math.stat_manager.check_hit", return_value=True), \
             patch("combat.engine.combat_math.roll_evade", return_value=False), \
             patch("combat.engine.combat_math.roll_parry", return_value=True):
            hit, msg = CombatMath.check_hit(self.attacker, self.target)
        self.assertFalse(hit)
        self.assertIn("parries", msg)

    def test_calculate_damage(self):
        from combat.engine import CombatMath
        weapon = {"damage": 4, "damage_type": DamageType.SLASHING}
        with patch("combat.engine.combat_math.state_manager.get_effective_stat") as mock_get, \
             patch("random.choice", return_value=HitLocation("torso", damage_mod=1.0)):
            mock_get.side_effect = lambda obj, stat: 10 if stat == "STR" else 0
            dmg, dtype, _ = CombatMath.calculate_damage(self.attacker, weapon, self.target)
        self.assertEqual(dtype, DamageType.SLASHING)
        self.assertEqual(dmg, int(round(4 * (1 + 10 * 0.05))))

    def test_damage_mapping_stable_order(self):
        """Weapon damage mapping should produce consistent results regardless of key order."""
        from combat.engine import CombatMath

        weapon = MagicMock()
        weapon.damage = None
        weapon.damage_type = None
        weapon.db = MagicMock()
        weapon.db.damage_dice = None
        weapon.db.dmg = None

        mapping1 = {
            DamageType.FIRE: "1",
            DamageType.ACID: "1",
        }
        mapping2 = {
            DamageType.ACID: "1",
            DamageType.FIRE: "1",
        }

        with patch("combat.engine.combat_math.roll_dice_string", return_value=1), \
             patch("combat.engine.combat_math.state_manager.get_effective_stat", side_effect=lambda obj, stat: 0), \
             patch("random.choice", return_value=HitLocation("torso", damage_mod=1.0)):
            weapon.db.damage = mapping1
            dmg1, dtype1, _ = CombatMath.calculate_damage(self.attacker, weapon, self.target)

        with patch("combat.engine.combat_math.roll_dice_string", return_value=1), \
             patch("combat.engine.combat_math.state_manager.get_effective_stat", side_effect=lambda obj, stat: 0), \
             patch("random.choice", return_value=HitLocation("torso", damage_mod=1.0)):
            weapon.db.damage = mapping2
            dmg2, dtype2, _ = CombatMath.calculate_damage(self.attacker, weapon, self.target)

        self.assertEqual(dmg1, dmg2)
        self.assertEqual(dtype1, dtype2)

    def test_damage_bonus_applied_and_scaled(self):
        """Damage bonus should be added before stat scaling."""
        from combat.engine import CombatMath

        weapon = MagicMock()
        weapon.damage = None
        weapon.damage_type = None
        weapon.db = MagicMock()
        weapon.db.damage = None
        weapon.db.damage_dice = "1d4"
        weapon.db.damage_bonus = 5

        with patch("combat.engine.combat_math.roll_dice_string", return_value=2), \
             patch(
                 "combat.engine.combat_math.state_manager.get_effective_stat",
                 side_effect=lambda obj, stat: 10 if stat == "STR" else 0,
             ), \
             patch("random.choice", return_value=HitLocation("torso", damage_mod=1.0)):
            dmg, dtype, _ = CombatMath.calculate_damage(self.attacker, weapon, self.target)

        expected = int(round((2 + 5) * (1 + 10 * 0.05)))
        self.assertEqual(dmg, expected)
        self.assertEqual(dtype, DamageType.BLUDGEONING)

    def test_damage_default_dice_and_bonus(self):
        """Missing damage_dice should fallback to '2d6' and include bonus."""
        from combat.engine import CombatMath

        weapon = MagicMock()
        weapon.damage = None
        weapon.damage_type = None
        weapon.db = MagicMock()
        weapon.db.damage = None
        weapon.db.damage_dice = None
        weapon.db.damage_bonus = 1

        with patch("combat.engine.combat_math.roll_dice_string", return_value=2) as mock_roll, \
             patch(
                 "combat.engine.combat_math.state_manager.get_effective_stat",
                 side_effect=lambda obj, stat: 0,
             ), \
             patch("random.choice", return_value=HitLocation("torso", damage_mod=1.0)):
            dmg, dtype, _ = CombatMath.calculate_damage(self.attacker, weapon, self.target)

        mock_roll.assert_called_once_with("2d6")
        self.assertEqual(dmg, 3)
        self.assertEqual(dtype, DamageType.BLUDGEONING)

    def test_apply_critical(self):
        from combat.engine import CombatMath
        with patch("combat.engine.combat_math.stat_manager.roll_crit", return_value=True), \
             patch("combat.engine.combat_math.stat_manager.crit_damage", return_value=8):
            dmg, crit = CombatMath.apply_critical(self.attacker, self.target, 5)
        self.assertTrue(crit)
        self.assertEqual(dmg, 8)

    def test_hit_location_modifies_damage(self):
        from combat.engine import CombatMath
        from combat.body_parts import HitLocation

        weapon = {"damage": 4, "damage_type": DamageType.BLUDGEONING}
        loc = HitLocation("head", damage_mod=2.0)
        with patch("combat.engine.combat_math.state_manager.get_effective_stat", side_effect=lambda o, s: 0), \
             patch("random.choice", return_value=loc):
            dmg, dtype, location = CombatMath.calculate_damage(self.attacker, weapon, self.target)

        self.assertEqual(location, loc)
        self.assertEqual(dmg, 8)


if __name__ == "__main__":  # pragma: no cover - manual run
    unittest.main()
