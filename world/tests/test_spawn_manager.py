from unittest import mock
from evennia.utils.test_resources import EvenniaTest
from evennia import create_object

from typeclasses.rooms import Room
from typeclasses.npcs import BaseNPC
from scripts.spawn_manager import SpawnManager


class TestSpawnManager(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.room = create_object(Room, key="room")
        self.room.set_area("testarea", 1)
        self.script = SpawnManager()
        self.script.at_script_creation()

    def test_reset_area_spawns_npc(self):
        self.script.db.entries = [
            {
                "area": "testarea",
                "prototype": "basic_merchant",
                "room": 1,
                "max_count": 2,
                "respawn_rate": 5,
                "last_spawn": 0,
            }
        ]
        self.script.force_respawn(1)
        npcs = [obj for obj in self.room.contents if obj.is_typeclass(BaseNPC, exact=False)]
        self.assertEqual(len(npcs), 1)
        self.assertEqual(npcs[0].db.prototype_key, "basic_merchant")

    def test_reload_spawns_forces_respawn(self):
        """reload_spawns should trigger force_respawn for each room."""
        self.script.db.entries = [
            {"room": 1},
            {"room": 2},
        ]
        with mock.patch.object(self.script, "load_spawn_data"), \
             mock.patch.object(self.script, "at_start") as mock_start, \
             mock.patch.object(self.script, "force_respawn") as mock_force:
            self.script.reload_spawns()
            mock_start.assert_called_once()
            mock_force.assert_any_call(1)
            mock_force.assert_any_call(2)
            self.assertEqual(mock_force.call_count, 2)
