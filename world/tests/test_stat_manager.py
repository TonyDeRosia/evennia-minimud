from evennia.utils.test_resources import EvenniaTest
from world.system import stat_manager


class Dummy:
    def __init__(self):
        self.db = type("DB", (), {})()
        # intentionally no traits attribute


class TestStatManager(EvenniaTest):
    def test_refresh_stats_without_traits(self):
        obj = Dummy()
        # should not raise when traits are missing
        stat_manager.refresh_stats(obj)

