import json
from unittest.mock import patch, MagicMock
from tempfile import TemporaryDirectory
from pathlib import Path
from django.test import override_settings
from evennia.utils.test_resources import EvenniaTest
from commands.admin import BuilderCmdSet
from typeclasses.rooms import Room
from world.areas import Area
from commands import aedit
from utils import prototype_manager


@override_settings(DEFAULT_HOME=None)
class TestASaveSpawns(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.char1.permissions.add("Builder")
        self.char1.cmdset.add_default(BuilderCmdSet)
        self.char1.msg = MagicMock()
        self.tmp = TemporaryDirectory()
        patcher = patch.dict(
            prototype_manager.CATEGORY_DIRS, {"room": Path(self.tmp.name)}
        )
        self.addCleanup(self.tmp.cleanup)
        self.addCleanup(patcher.stop)
        patcher.start()

    def test_asave_keeps_spawns(self):
        room = self.room1
        room.db.room_id = 1
        room.db.area = "zone"
        room.db.exits = {}
        proto = {
            "vnum": 1,
            "area": "zone",
            "spawns": [{"prototype": "goblin", "max_spawns": 2, "spawn_interval": 10}],
        }
        path = Path(self.tmp.name) / "1.json"
        with path.open("w") as f:
            json.dump(proto, f)

        area = Area(key="zone", start=1, end=1, rooms=[1])

        def _filter(**kwargs):
            val = kwargs.get("db_attributes__db_value")
            return [room] if val == 1 else []

        with (
            patch("commands.aedit.get_areas", return_value=[area]),
            patch("commands.aedit.ObjectDB.objects.filter", side_effect=_filter),
            patch("commands.aedit.save_prototype") as mock_save,
            patch("commands.aedit.update_area"),
            patch("commands.aedit.refresh_coordinates"),
        ):
            cmd = aedit.CmdASave()
            cmd.caller = self.char1
            cmd.session = self.char1.sessions.get()
            cmd.args = "changed"
            cmd.func()

        saved = mock_save.call_args[0][1]
        assert saved["spawns"] == proto["spawns"]
