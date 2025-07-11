from unittest.mock import MagicMock, patch
from django.test import override_settings
from evennia.utils.test_resources import EvenniaTest
from commands.admin import BuilderCmdSet
from world.areas import Area


@override_settings(DEFAULT_HOME=None)
class TestAListCommand(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.char1.msg = MagicMock()
        self.char1.cmdset.add_default(BuilderCmdSet)
        self.room1.set_area("zone", 1)
        self.room2.set_area("zone", 2)

    @patch("commands.aedit.get_areas")
    @patch("commands.aedit.area_npcs.get_area_npc_list")
    def test_counts_display(self, mock_npcs, mock_get_areas):
        mock_get_areas.return_value = [Area(key="zone", start=1, end=5)]
        mock_npcs.return_value = ["gob", "orc"]
        self.char1.execute_cmd("alist")
        out = self.char1.msg.call_args[0][0]
        self.assertIn("Rooms", out)
        self.assertIn("Vnums", out)
        self.assertIn("Mobs", out)
        row = next(line for line in out.splitlines() if line.startswith("| zone"))
        cols = [c.strip() for c in row.split("|")[1:-1]]
        self.assertEqual(cols[2], "2")
        self.assertEqual(cols[3], "1, 2")
        self.assertEqual(cols[4], "2")

    @patch("commands.aedit.load_all_prototypes")
    @patch("commands.aedit.get_areas")
    def test_fallback_from_rooms_and_prototypes(self, mock_get_areas, mock_load):
        mock_get_areas.return_value = []

        def _load(category):
            if category == "room":
                return {
                    3: {"area": "zone", "room_id": 3},
                    4: {"area": "zone", "room_id": 4},
                }
            if category == "npc":
                return {10: {"area": "zone"}}
            return {}

        mock_load.side_effect = _load
        self.char1.execute_cmd("alist")
        out = self.char1.msg.call_args[0][0]
        row = next(line for line in out.splitlines() if line.startswith("| zone"))
        cols = [c.strip() for c in row.split("|")[1:-1]]
        self.assertEqual(cols[1], "1-4")
        self.assertEqual(cols[2], "4")
        self.assertEqual(cols[3], "1, 2, 3, 4")
        self.assertEqual(cols[4], "1")

    @patch("commands.aedit.ObjectDB.objects.filter", return_value=[])
    @patch("commands.aedit.get_areas")
    @patch("commands.aedit.area_npcs.get_area_npc_list")
    def test_counts_from_metadata(self, mock_npcs, mock_get_areas, mock_filter):
        area = Area(key="zone", start=1, end=5, rooms=[1, 2, 3])
        mock_get_areas.return_value = [area]
        mock_npcs.return_value = ["orc"]
        self.char1.execute_cmd("alist")
        out = self.char1.msg.call_args[0][0]
        row = next(line for line in out.splitlines() if line.startswith("| zone"))
        cols = [c.strip() for c in row.split("|")[1:-1]]
        self.assertEqual(cols[2], "3")
        self.assertEqual(cols[3], "1, 2, 3")
        self.assertEqual(cols[4], "1")

    @patch("commands.aedit.ObjectDB.objects.filter", return_value=[])
    @patch("commands.aedit.get_areas")
    @patch("commands.aedit.area_npcs.get_area_npc_list")
    def test_vnums_truncated(self, mock_npcs, mock_get_areas, mock_filter):
        area = Area(key="zone", start=1, end=100, rooms=list(range(1, 30)))
        mock_get_areas.return_value = [area]
        mock_npcs.return_value = []
        self.char1.execute_cmd("alist")
        out = self.char1.msg.call_args[0][0]
        row = next(line for line in out.splitlines() if line.startswith("| zone"))
        cols = [c.strip() for c in row.split("|")[1:-1]]
        self.assertLessEqual(len(cols[3]), 60)
        self.assertTrue(cols[3].endswith("..."))

    def test_current(self):
        self.char1.location = self.room1
        self.char1.execute_cmd("alist current")
        out = self.char1.msg.call_args[0][0]
        self.assertIn("Current area: zone", out)

