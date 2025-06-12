import json
from unittest import mock
from tempfile import TemporaryDirectory
from pathlib import Path

import django
from django.conf import settings
from django.test import override_settings
from evennia.utils.test_resources import EvenniaTest

from utils import vnum_registry
from world.areas import Area


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
        area = Area(key="town", start=100, end=105, reset_interval=0)
        with mock.patch("world.areas.get_area_vnum_range", return_value=(100, 105)), \
             mock.patch("world.areas.find_area", return_value=(0, area)):
            val1 = vnum_registry.get_next_vnum_for_area("town", "npc", builder=None)
            self.assertEqual(val1, 100)
            val2 = vnum_registry.get_next_vnum_for_area("town", "npc", builder=None)
            self.assertEqual(val2, 101)
            data = json.load(open(Path(self.tmp.name) / "vnums.json"))
            self.assertIn(100, data["npc"]["used"])
            self.assertIn(101, data["npc"]["used"])

    def test_builder_permissions(self):
        area = Area(key="town", start=100, end=105, builders=["Alice"], reset_interval=0)
        with mock.patch("world.areas.get_area_vnum_range", return_value=(100, 105)), \
             mock.patch("world.areas.find_area", return_value=(0, area)):
            with self.assertRaises(PermissionError):
                vnum_registry.get_next_vnum_for_area("town", "npc", builder="Bob")
        with mock.patch("world.areas.get_area_vnum_range", return_value=(100, 105)), \
             mock.patch("world.areas.find_area", return_value=(0, area)):
            vnum_registry.get_next_vnum_for_area("town", "npc", builder="Alice")

