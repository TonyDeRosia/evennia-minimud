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


class TestActionUtils(unittest.TestCase):
    def setUp(self):
        self.attacker = MagicMock(key="Attacker")
        self.target = MagicMock(key="Target")

    def test_check_hit_miss(self):
        from combat.actions import utils
        with patch("combat.actions.utils.stat_manager.check_hit", return_value=False):
            hit, msg = utils.check_hit(self.attacker, self.target)
        self.assertFalse(hit)
        self.assertIn("misses", msg)

    def test_check_hit_parry(self):
        from combat.actions import utils
        with patch("combat.actions.utils.stat_manager.check_hit", return_value=True), \
             patch("combat.actions.utils.roll_evade", return_value=False), \
             patch("combat.actions.utils.roll_parry", return_value=True):
            hit, msg = utils.check_hit(self.attacker, self.target)
        self.assertFalse(hit)
        self.assertIn("parries", msg)

    def test_calculate_damage(self):
        from combat.actions import utils
        weapon = {"damage": 4, "damage_type": DamageType.SLASHING}
        with patch("combat.actions.utils.state_manager.get_effective_stat") as mock_get:
            mock_get.side_effect = lambda obj, stat: 10 if stat == "STR" else 0
            dmg, dtype = utils.calculate_damage(self.attacker, weapon, self.target)
        self.assertEqual(dtype, DamageType.SLASHING)
        self.assertEqual(dmg, int(round(4 * (1 + 10 * 0.012))))

    def test_apply_critical(self):
        from combat.actions import utils
        with patch("combat.actions.utils.stat_manager.roll_crit", return_value=True), \
             patch("combat.actions.utils.stat_manager.crit_damage", return_value=8):
            dmg, crit = utils.apply_critical(self.attacker, self.target, 5)
        self.assertTrue(crit)
        self.assertEqual(dmg, 8)


if __name__ == "__main__":  # pragma: no cover - manual run
    unittest.main()
