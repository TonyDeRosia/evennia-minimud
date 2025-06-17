import json
from unittest.mock import patch, MagicMock
from tempfile import TemporaryDirectory
from pathlib import Path
from django.test import override_settings
from evennia.utils.test_resources import EvenniaTest


@override_settings(DEFAULT_HOME=None)
class TestRRegAreaFile(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.tmp = TemporaryDirectory()
        # patch area storage path
        patcher = patch('world.areas._BASE_PATH', Path(self.tmp.name))
        self.addCleanup(self.tmp.cleanup)
        self.addCleanup(patcher.stop)
        patcher.start()
        self.char1.msg = MagicMock()
        self.char1.execute_cmd("amake zone 1-10")
        self.area_file = Path(self.tmp.name) / "zone.json"
        self.char1.msg.reset_mock()

    def test_rreg_updates_rooms_list(self):
        with self.area_file.open() as f:
            data = json.load(f)
        self.assertEqual(data.get("rooms"), [])
        self.char1.execute_cmd("rreg zone 3")
        with self.area_file.open() as f:
            data = json.load(f)
        self.assertIn(3, data.get("rooms", []))
        self.assertEqual(len(data["rooms"]), 1)

