import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
import django
import evennia
import unittest
from unittest.mock import patch, MagicMock

django.setup()
if getattr(evennia, "SESSION_HANDLER", None) is None:
    evennia._init()

from utils import script_utils


class TestScriptUtils(unittest.TestCase):
    def test_get_spawn_manager_filters_key(self):
        with patch("utils.script_utils.ScriptDB.objects.filter") as mock_filter:
            mock_filter.return_value.first.return_value = "script"
            result = script_utils.get_spawn_manager()
            self.assertEqual(result, "script")
            mock_filter.assert_called_with(db_key="spawn_manager")

    def test_respawn_area_calls_force_respawn(self):
        mock_script = MagicMock()
        room1 = MagicMock()
        room1.db.spawn_entries = [1]
        room1.db.room_id = 1
        room1.attributes.get.return_value = "zone"
        room3 = MagicMock()
        room3.db.spawn_entries = [1]
        room3.db.room_id = 3
        room3.attributes.get.return_value = "zone"
        with patch("utils.script_utils.get_spawn_manager", return_value=mock_script), \
             patch("utils.script_utils.ObjectDB.objects.get_by_attribute", return_value=[room1, room3]):
            script_utils.respawn_area("zone")
        mock_script.force_respawn.assert_any_call(1)
        mock_script.force_respawn.assert_any_call(3)
        self.assertEqual(mock_script.force_respawn.call_count, 2)

    def test_respawn_area_missing_manager(self):
        with patch("utils.script_utils.get_spawn_manager", return_value=None):
            script_utils.respawn_area("zone")

