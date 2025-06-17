from unittest import mock, TestCase
from evennia.utils.test_resources import EvenniaTest
from evennia import create_object

from typeclasses.rooms import Room
from typeclasses.npcs import BaseNPC
from scripts.spawn_manager import SpawnManager


class TestSpawnManager(EvenniaTest):
    def setUp(self):
        from django.conf import settings
        settings.TEST_ENVIRONMENT = True
        super().setUp()
        self.room = create_object(Room, key="room")
        self.room.set_area("testarea", 1)
        from evennia.utils import create
        self.script = create.create_script(SpawnManager, key="spawn_manager")

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
        npc = create_object(BaseNPC, key="basic_merchant")
        with mock.patch(
            "scripts.spawn_manager.prototypes.get_npc_prototypes",
            return_value={"basic_merchant": {"key": "basic_merchant"}},
        ), mock.patch(
            "evennia.prototypes.spawner.spawn", return_value=[npc]
        ):
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

    def test_load_spawn_data_numeric_proto(self):
        obj = create_object(BaseNPC, key="num")
        with mock.patch("utils.prototype_manager.load_all_prototypes") as m_load, \
             mock.patch("world.prototypes.get_npc_prototypes", return_value={}) as m_npcs, \
             mock.patch("world.scripts.mob_db.get_mobdb") as m_db, \
             mock.patch("scripts.spawn_manager.spawn_from_vnum") as m_spawn, \
             mock.patch("evennia.utils.logger.log_err") as m_log:
            m_load.return_value = {
                1: {
                    "vnum": 1,
                    "area": "testarea",
                    "spawns": [{"prototype": 5}],
                }
            }
            fake = mock.Mock()
            fake.get_proto.return_value = {"key": "num"}
            m_db.return_value = fake

            def side(vnum, location=None):
                obj.location = location
                return obj

            m_spawn.side_effect = side

            self.script.load_spawn_data()
            self.script.force_respawn(1)

        self.assertEqual(len(self.script.db.entries), 1)
        self.assertEqual(self.script.db.entries[0]["prototype"], 5)
        self.assertEqual(obj.location, self.room)
        fake.get_proto.assert_called_with(5)
        m_spawn.assert_called_with(5, location=self.room)
        m_log.assert_not_called()

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

    def test_spawn_numeric_finalized_once(self):
        npc = create_object(BaseNPC, key="num")
        with mock.patch("scripts.spawn_manager.spawn_from_vnum") as m_spawn, \
             mock.patch("commands.npc_builder.finalize_mob_prototype") as m_fin:

            def side(vnum, location=None):
                npc.location = location
                m_fin(npc, npc)
                return npc

            m_spawn.side_effect = side
            self.script._spawn(5, self.room)

        self.assertEqual(m_fin.call_count, 1)



    def test_spawn_key_finalized_once(self):
        npc = create_object(BaseNPC, key="orc")
        with mock.patch(
            "scripts.spawn_manager.prototypes.get_npc_prototypes",
            return_value={"orc": {"key": "orc"}},
        ), mock.patch(
            "evennia.prototypes.spawner.spawn", return_value=[npc]
        ), mock.patch(
            "scripts.spawn_manager.apply_proto_items"
        ), mock.patch(
            "commands.npc_builder.finalize_mob_prototype"
        ) as m_fin:
            self.script._spawn("orc", self.room)

        self.assertEqual(m_fin.call_count, 1)


class TestGetRoomCaching(TestCase):
    def test_get_room_caches_result(self):
        import world.tests  # noqa: F401 - triggers django setup
        mgr = SpawnManager()
        entry = {"room": "#10", "room_id": 10}
        room = mock.Mock()
        room.id = 10
        room.db.room_id = 10
        with mock.patch("scripts.spawn_manager.ObjectDB.objects") as m_obj, \
             mock.patch("scripts.spawn_manager.search.search_object") as m_search:
            m_obj.filter.return_value.first.return_value = room
            m_obj.get_by_attribute.return_value = [room]
            m_search.return_value = []

            result1 = mgr._get_room(entry)
            result2 = mgr._get_room(entry)

        self.assertIs(result1, room)
        self.assertIs(result2, room)
        m_obj.filter.assert_called_once()
        m_obj.get_by_attribute.assert_not_called()
        m_search.assert_not_called()
