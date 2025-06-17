from unittest import mock
from evennia.utils.test_resources import EvenniaTest
from world.area_reset import AreaReset
from world.areas import Area

class TestAreaReset(EvenniaTest):
    def test_age_increment_and_reset(self):
        area = Area(key="town", start=1, end=10, reset_interval=2)
        areas = [area]
        with mock.patch("world.area_reset.get_areas", return_value=areas), \
             mock.patch("world.area_reset.update_area") as mock_update, \
             mock.patch("world.area_reset.spawn_manager.SpawnManager.reset_area") as mock_reset:
            script = AreaReset()
            script.at_script_creation()
            script.at_repeat()
            self.assertEqual(area.age, 1)
            script.at_repeat()
            self.assertEqual(area.age, 0)
            self.assertTrue(mock_update.called)
            mock_reset.assert_called_with("town")

