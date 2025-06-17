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
             mock.patch("world.area_reset.ScriptDB") as mock_sdb:
            mock_script = mock.MagicMock()
            mock_sdb.objects.filter.return_value.first.return_value = mock_script
            script = AreaReset()
            script.at_script_creation()
            script.at_repeat()
            self.assertEqual(area.age, 1)
            script.at_repeat()
            self.assertEqual(area.age, 0)
            self.assertTrue(mock_update.called)
            self.assertTrue(mock_script.force_respawn.called)

