from unittest.mock import MagicMock

from evennia.utils.test_resources import EvenniaTest


class TestTrainingPoints(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.char1.msg = MagicMock()

    def test_trainres_increases_stat(self):
        from world.system import stat_manager

        self.char1.db.training_points = 3
        base = self.char1.traits.health.base

        self.char1.execute_cmd("trainres hp 2")

        stat_manager.refresh_stats(self.char1)
        self.assertEqual(self.char1.db.training_points, 1)
        self.assertEqual(self.char1.traits.health.base, base + 2)
