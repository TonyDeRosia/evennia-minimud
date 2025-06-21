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
        mock_script.db.entries = [
            {"area": "zone", "room_id": 1},
            {"area": "town", "room_id": 2},
            {"area": "zone", "room_id": 3},
        ]
        mock_script._normalize_room_id.side_effect = lambda entry: entry.get("room_id")
        with patch("utils.script_utils.get_spawn_manager", return_value=mock_script):
            script_utils.respawn_area("zone")
        mock_script.force_respawn.assert_any_call(1)
        mock_script.force_respawn.assert_any_call(3)
        self.assertEqual(mock_script.force_respawn.call_count, 2)

    def test_respawn_area_missing_manager(self):
        with patch("utils.script_utils.get_spawn_manager", return_value=None):
            script_utils.respawn_area("zone")

