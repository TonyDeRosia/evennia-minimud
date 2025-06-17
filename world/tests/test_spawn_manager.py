from unittest import mock
from evennia.utils.test_resources import EvenniaTest
from evennia import create_object

from typeclasses.rooms import Room
from typeclasses.npcs import BaseNPC
from world.scripts.spawn import SpawnManager


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
                "initial_count": 1,
                "max_count": 2,
                "respawn_rate": 5,
                "last_spawn": 0,
            }
        ]
        self.script.force_respawn(1)
        npcs = [obj for obj in self.room.contents if obj.is_typeclass(BaseNPC, exact=False)]
        self.assertEqual(len(npcs), 1)
        self.assertEqual(npcs[0].db.prototype_key, "basic_merchant")
