from unittest import mock
from evennia.utils.test_resources import EvenniaTest
from evennia import create_object

from typeclasses.rooms import Room
from typeclasses.npcs import BaseNPC
from world.spawn_manager import SpawnManager, SpawnEntry


class TestSpawnManager(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.room = create_object(Room, key="room")
        self.room.set_area("testarea", 1)
        # clear registry
        SpawnManager._save_registry([])

    def test_reset_area_spawns_npc(self):
        entry = SpawnEntry(area="testarea", proto="basic_merchant", room=1, initial_count=1, max_count=2)
        SpawnManager._save_registry([entry.to_dict()])
        SpawnManager.reset_area("testarea")
        npcs = [obj for obj in self.room.contents if obj.is_typeclass(BaseNPC, exact=False)]
        self.assertEqual(len(npcs), 1)
        self.assertEqual(npcs[0].db.prototype_key, "basic_merchant")
