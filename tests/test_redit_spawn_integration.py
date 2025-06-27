from unittest.mock import MagicMock, patch

from django.test import override_settings
from evennia.utils import create
from evennia.utils.test_resources import EvenniaTest

from commands import redit
from commands.admin import BuilderCmdSet
from scripts.mob_respawn_manager import MobRespawnManager
from typeclasses.npcs import BaseNPC
from typeclasses.rooms import Room
from world.areas import Area


@override_settings(DEFAULT_HOME=None)
class TestReditSpawnIntegration(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.char1.msg = MagicMock()
        self.char1.cmdset.add_default(BuilderCmdSet)
        self.room = create.create_object(
            Room, key="R1", location=self.char1.location, home=self.char1.location
        )
        self.room.db.room_id = 5
        self.room.db.area = "zone"
        self.char1.location = self.room
        self.script = MobRespawnManager()
        self.script.at_script_creation()

    def test_spawn_manager_integration(self):
        area = Area(key="zone", start=1, end=10)
        with (
            patch("commands.redit.validate_vnum", return_value=True),
            patch("commands.redit.register_vnum"),
            patch("commands.redit.load_prototype", return_value=None),
            patch("commands.redit.spawner.spawn", return_value=[self.room]),
            patch("commands.redit.find_area_by_vnum", return_value=area),
            patch("commands.redit.find_area", return_value=(0, area)),
            patch("commands.redit.save_prototype"),
            patch("commands.redit.OLCEditor"),
        ):
            self.char1.execute_cmd("redit create 5")

        redit._handle_spawn_cmd(self.char1, "add slime 1 5")
        proto = self.char1.ndb.room_protos[5]
        self.char1.ndb.room_protos[5] = proto

        self.script.register_room_spawn = MagicMock(
            wraps=self.script.register_room_spawn
        )
        self.script.force_respawn = MagicMock(wraps=self.script.force_respawn)

        with (
            patch("commands.redit.save_prototype"),
            patch("commands.redit.ObjectDB.objects.filter", return_value=[self.room]),
            patch("commands.redit.get_respawn_manager", return_value=self.script),
            patch.object(self.script, "_spawn") as mock_spawn,
        ):
            mock_spawn.side_effect = lambda proto, room: create.create_object(
                BaseNPC, key=str(proto), location=room
            )
            redit.menunode_done(self.char1)

        self.script.register_room_spawn.assert_called_with(proto)
        self.script.force_respawn.assert_called_with(5)
        npcs = [
            obj for obj in self.room.contents if obj.is_typeclass(BaseNPC, exact=False)
        ]
        assert len(npcs) == 1
        assert npcs[0].key == "slime"
        assert proto["vnum"] == 5

    def test_invalid_proto_not_added(self):
        area = Area(key="zone", start=1, end=10)
        with (
            patch("commands.redit.validate_vnum", return_value=True),
            patch("commands.redit.register_vnum"),
            patch("commands.redit.load_prototype", return_value=None),
            patch("commands.redit.spawner.spawn", return_value=[self.room]),
            patch("commands.redit.find_area_by_vnum", return_value=area),
            patch("commands.redit.find_area", return_value=(0, area)),
            patch("commands.redit.save_prototype"),
            patch("commands.redit.OLCEditor"),
        ):
            self.char1.execute_cmd("redit create 5")

        self.char1.msg.reset_mock()

        with (
            patch("commands.redit.get_mobdb") as mock_db,
            patch("commands.redit.prototypes.get_npc_prototypes", return_value={}),
        ):
            mock_db.return_value.get_proto.return_value = None
            result = redit._handle_spawn_cmd(self.char1, "add unknown 1 5")

        assert result == "menunode_spawns"
        assert not self.char1.ndb.room_protos[5]["spawns"]
        self.char1.msg.assert_any_call("Prototype not found.")
