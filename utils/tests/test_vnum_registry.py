import json
from unittest import mock
from tempfile import TemporaryDirectory
from pathlib import Path

import django
from django.conf import settings
from django.test import override_settings
from evennia.utils.test_resources import EvenniaTest

from utils import vnum_registry


@override_settings(DEFAULT_HOME=None)
class TestVnumRegistry(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.tmp = TemporaryDirectory()
        patcher = mock.patch.object(
            settings,
            "VNUM_REGISTRY_FILE",
            Path(self.tmp.name) / "vnums.json",
        )
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(self.tmp.cleanup)

    def test_next_vnum_for_area(self):
        with mock.patch("world.areas.get_area_vnum_range", return_value=(100, 105)):
            val1 = vnum_registry.get_next_vnum_for_area("town", "npc")
            self.assertEqual(val1, 100)
            val2 = vnum_registry.get_next_vnum_for_area("town", "npc")
            self.assertEqual(val2, 101)
            data = json.load(open(Path(self.tmp.name) / "vnums.json"))
            self.assertIn(100, data["npc"]["used"])
            self.assertIn(101, data["npc"]["used"])

