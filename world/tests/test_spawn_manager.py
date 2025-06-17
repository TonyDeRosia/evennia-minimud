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

    def test_load_spawn_data_skips_missing_proto(self):
        with mock.patch("utils.prototype_manager.load_all_prototypes") as m_load, \
             mock.patch("world.prototypes.get_npc_prototypes") as m_npcs, \
             mock.patch("evennia.utils.logger.log_err") as m_log:
            m_load.return_value = {
                1: {
                    "vnum": 1,
                    "area": "testarea",
                    "spawns": [
                        {"prototype": "valid_proto"},
                        {"prototype": "missing_proto"},
                    ],
                }
            }
            m_npcs.return_value = {"valid_proto": {}}
            self.script.load_spawn_data()
        self.assertEqual(len(self.script.db.entries), 1)
        self.assertEqual(self.script.db.entries[0]["prototype"], "valid_proto")
        m_log.assert_called_once()
