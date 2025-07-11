from unittest.mock import patch
from evennia.utils.test_resources import EvenniaTest
from django.test import override_settings
from world.system import stat_manager


@override_settings(DEFAULT_HOME=None)
class TestCombatCalculations(EvenniaTest):
    def test_check_hit_uses_hit_chance_and_dodge(self):
        self.char1.db.stat_overrides = {"hit_chance": 100}
        self.char2.db.stat_overrides = {"dodge": 0}
        stat_manager.refresh_stats(self.char1)
        stat_manager.refresh_stats(self.char2)
        with patch("world.system.stat_manager.randint", return_value=100):
            self.assertFalse(stat_manager.check_hit(self.char1, self.char2))
        self.char2.db.stat_overrides = {"dodge": 200}
        stat_manager.refresh_stats(self.char2)
        with patch("world.system.stat_manager.randint", return_value=1):
            self.assertTrue(stat_manager.check_hit(self.char1, self.char2))

    def test_roll_crit_respects_resist(self):
        self.char1.db.stat_overrides = {"crit_chance": 50}
        self.char2.db.stat_overrides = {"crit_resist": 20}
        stat_manager.refresh_stats(self.char1)
        stat_manager.refresh_stats(self.char2)
        with patch("world.system.stat_manager.randint", return_value=10):
            self.assertTrue(stat_manager.roll_crit(self.char1, self.char2))
        self.char2.db.stat_overrides = {"crit_resist": 60}
        stat_manager.refresh_stats(self.char2)
        with patch("world.system.stat_manager.randint", return_value=10):
            self.assertFalse(stat_manager.roll_crit(self.char1, self.char2))

    def test_roll_status_with_resist(self):
        self.char2.db.stat_overrides = {"status_resist": 50}
        stat_manager.refresh_stats(self.char2)
        with patch("world.system.stat_manager.randint", return_value=40):
            self.assertFalse(stat_manager.roll_status(self.char1, self.char2, 40))
        self.char2.db.stat_overrides = {"status_resist": 0}
        stat_manager.refresh_stats(self.char2)
        with patch("world.system.stat_manager.randint", return_value=40):
            self.assertTrue(stat_manager.roll_status(self.char1, self.char2, 40))

    def test_crit_damage_applies_bonus(self):
        self.char1.db.stat_overrides = {"crit_bonus": 50}
        stat_manager.refresh_stats(self.char1)
        self.assertEqual(stat_manager.crit_damage(self.char1, 10), 15)


@override_settings(DEFAULT_HOME=None)
class TestCombatUtils(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.char1.key = "Attacker"
        self.char2.key = "Target"

    def test_roll_crit_and_damage(self):
        from combat import combat_utils

        self.char1.db.stat_overrides = {"crit_chance": 60, "crit_bonus": 50}
        self.char2.db.stat_overrides = {"crit_resist": 0}
        stat_manager.refresh_stats(self.char1)
        stat_manager.refresh_stats(self.char2)
        with patch("world.system.stat_manager.randint", return_value=10):
            self.assertTrue(stat_manager.roll_crit(self.char1, self.char2))
        self.assertEqual(stat_manager.crit_damage(self.char1, 10), 15)

    def test_roll_evade(self):
        from combat import combat_utils

        self.char1.db.stat_overrides = {"hit_chance": 0}
        self.char2.db.stat_overrides = {"evasion": 40}
        stat_manager.refresh_stats(self.char1)
        stat_manager.refresh_stats(self.char2)
        with patch("combat.combat_utils.random.randint", return_value=10):
            self.assertTrue(combat_utils.roll_evade(self.char1, self.char2))
        with patch("combat.combat_utils.random.randint", return_value=95):
            self.assertFalse(combat_utils.roll_evade(self.char1, self.char2))

    def test_distance_and_format_message(self):
        from combat import combat_utils

        class DummyRoom:
            def __init__(self, xyz):
                self.xyz = xyz

        room1 = DummyRoom((0, 0, 0))
        room2 = DummyRoom((2, 1, 0))
        self.assertEqual(combat_utils.get_distance(room1, room2), 3)
        self.assertTrue(combat_utils.check_distance(room1, room2, 3))
        self.assertFalse(combat_utils.check_distance(room1, room2, 2))

        msg = combat_utils.format_combat_message(
            self.char1, self.char2, "hits", damage=5, crit=True
        )
        self.assertIn("Attacker", msg)
        self.assertIn("Target", msg)
        self.assertIn("5", msg)
        self.assertIn("critical", msg)

    def test_format_combat_message_colors(self):
        from combat import combat_utils

        self.char1.db.level = 20
        with patch("world.system.state_manager.get_effective_stat", return_value=0):
            max_range = self.char1.db.level * 5
            levels = [
                (int(max_range * 0.95), "|R"),
                (int(max_range * 0.65), "|r"),
                (int(max_range * 0.35), "|y"),
                (1, "|g"),
                (0, "|w"),
            ]
            for dmg, code in levels:
                msg = combat_utils.format_combat_message(
                    self.char1, self.char2, "hits", damage=dmg
                )
                self.assertIn(f"{code}{dmg}|n", msg)
                self.assertTrue(msg.startswith("Attacker"))
                self.assertIn("damage", msg)

    def test_get_condition_msg(self):
        from combat.combat_utils import get_condition_msg

        self.assertEqual(get_condition_msg(10, 10), "is in excellent condition.")
        self.assertEqual(get_condition_msg(9, 10), "has a few scratches.")
        self.assertEqual(get_condition_msg(7, 10), "has some wounds.")
        self.assertEqual(get_condition_msg(5, 10), "has nasty wounds.")
        self.assertEqual(get_condition_msg(3, 10), "is bleeding badly.")
        self.assertEqual(get_condition_msg(1, 10), "is in awful condition.")
        self.assertEqual(get_condition_msg(0, 10), "is dead.")

    def test_damage_adjectives(self):
        from combat import combat_utils

        self.char1.db.level = 20
        with patch("world.system.state_manager.get_effective_stat", return_value=0):
            max_range = self.char1.db.level * 5
            cases = [
                (int(max_range * 0.95), "legendary"),
                (int(max_range * 0.65), "heavy"),
                (int(max_range * 0.35), "solid"),
                (1, "light"),
                (0, ""),
            ]
            for dmg, word in cases:
                self.assertEqual(combat_utils.damage_adjective(self.char1, dmg), word)

            msg = combat_utils.format_combat_message(
                self.char1,
                self.char2,
                "hits",
                damage=int(max_range * 0.95),
                adjective=True,
            )
            self.assertIn("legendary", msg)

