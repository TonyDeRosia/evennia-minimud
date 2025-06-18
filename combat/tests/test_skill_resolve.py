import unittest
from unittest.mock import patch

from combat.combat_skills import Thrust, Cleave


class DummyChar:
    def __init__(self, key, hp=10):
        self.key = key
        self.hp = hp
        self.location = None

    def is_alive(self):
        return self.hp > 0


class DummyRoom:
    def __init__(self):
        self.contents = []


def make_room_with_targets(num_targets):
    room = DummyRoom()
    user = DummyChar("user")
    user.location = room
    room.contents.append(user)
    targets = []
    for i in range(num_targets):
        t = DummyChar(f"t{i}")
        t.location = room
        room.contents.append(t)
        targets.append(t)
    return user, targets, room


class TestThrustResolve(unittest.TestCase):
    def setUp(self):
        self.user = DummyChar("attacker")
        self.target = DummyChar("defender")

    def test_miss_does_no_damage(self):
        self.target.hp = 10
        with patch("world.system.stat_manager.check_hit", return_value=False), \
             patch("combat.combat_skills.roll_evade", return_value=False), \
             patch("combat.combat_skills.roll_damage", return_value=3):
            result = Thrust("thrust").resolve(self.user, self.target)
        self.assertIn("miss", result.message)
        self.assertEqual(self.target.hp, 10)

    def test_hit_applies_damage(self):
        self.target.hp = 10
        with patch("world.system.stat_manager.check_hit", return_value=True), \
             patch("combat.combat_skills.roll_evade", return_value=False), \
             patch("combat.combat_skills.roll_damage", return_value=4):
            result = Thrust("thrust").resolve(self.user, self.target)
        self.assertIn("thrusts", result.message)
        self.assertEqual(self.target.hp, 6)


class TestCleaveResolve(unittest.TestCase):
    def test_hits_up_to_three_targets(self):
        user, targets, room = make_room_with_targets(4)
        with patch("combat.combat_skills.random.sample", side_effect=lambda pop, k: pop[:k]) as sample, \
             patch("combat.combat_skills.random.randint", return_value=3), \
             patch("world.system.stat_manager.check_hit", return_value=True), \
             patch("combat.combat_skills.roll_evade", return_value=False), \
             patch("combat.combat_skills.roll_damage", return_value=2):
            result = Cleave("cleave").resolve(user, None)
        # only first three targets should take damage
        for t in targets[:3]:
            self.assertEqual(t.hp, 8)
        self.assertEqual(targets[3].hp, 10)
        # ensure message has one line per target
        lines = result.message.splitlines()
        self.assertEqual(len(lines), 3)
        for idx, line in enumerate(lines):
            self.assertIn(targets[idx].key, line)
        sample.assert_called()


if __name__ == "__main__":
    unittest.main()
