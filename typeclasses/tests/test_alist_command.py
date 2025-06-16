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
        self.assertIn("Mobs", out)
        row = next(line for line in out.splitlines() if line.startswith("| zone"))
        cols = [c.strip() for c in row.split("|")[1:-1]]
        self.assertEqual(cols[2], "2")
        self.assertEqual(cols[3], "2")

