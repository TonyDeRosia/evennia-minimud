from unittest.mock import MagicMock
from evennia.utils.test_resources import EvenniaTest
from world.system import state_manager


class TestLeveling(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.char1.db.exp = 0
        self.char1.db.level = 1
        self.char1.db.practice_sessions = 0
        self.char1.db.training_points = 0
        self.char1.msg = MagicMock()

    def test_single_level_up_awards_resources(self):
        self.char1.db.exp = 100
        state_manager.check_level_up(self.char1)
        self.assertEqual(self.char1.db.level, 2)
        self.assertEqual(self.char1.db.practice_sessions, 3)
        self.assertEqual(self.char1.db.training_points, 1)
        self.char1.msg.assert_called()
        output = self.char1.msg.call_args[0][0]
        self.assertIn("practice sessions", output)
        self.assertIn("training session", output)

    def test_multiple_level_ups(self):
        self.char1.db.exp = 210
        state_manager.check_level_up(self.char1)
        self.assertEqual(self.char1.db.level, 3)
        self.assertEqual(self.char1.db.practice_sessions, 6)
        self.assertEqual(self.char1.db.training_points, 2)
        output = self.char1.msg.call_args[0][0]
        self.assertIn("practice sessions", output)
        self.assertIn("training session", output)
