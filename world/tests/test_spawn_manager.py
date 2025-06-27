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
                "spawned": [],
                "dead_timestamps": [],
            }
        ]
        npc = create_object(BaseNPC, key="basic_merchant")
        with mock.patch("scripts.spawn_manager.prototypes.get_npc_prototypes", return_value={"basic_merchant": {"key": "basic_merchant"}}), \
             mock.patch("evennia.prototypes.spawner.spawn", return_value=[npc]):
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
                    "spawns": [{"prototype": "5"}],
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

    def test_force_respawn_numeric_string_limits_count(self):
        npc = create_object(BaseNPC, key="num")
        npc.db.prototype_key = 5
        npc.db.spawn_room = self.room
        npc.location = self.room

        self.script.db.entries = [
            {
                "area": "testarea",
                "prototype": "5",
                "room": 1,
                "room_id": 1,
                "max_count": 1,
                "respawn_rate": 5,
                "spawned": [],
                "dead_timestamps": [],
            }
        ]
        with mock.patch("scripts.spawn_manager.spawn_from_vnum") as m_spawn:
            self.script.force_respawn(1)

        self.assertEqual(m_spawn.call_count, 0)
        npcs = [obj for obj in self.room.contents if obj.is_typeclass(BaseNPC, exact=False)]
        self.assertEqual(len(npcs), 1)

    def test_spawn_key_finalized_once(self):
        npc = create_object(BaseNPC, key="orc")
        with mock.patch("scripts.spawn_manager.prototypes.get_npc_prototypes", return_value={"orc": {"key": "orc"}}), \
             mock.patch("evennia.prototypes.spawner.spawn", return_value=[npc]), \
             mock.patch("scripts.spawn_manager.apply_proto_items"), \
             mock.patch("commands.npc_builder.finalize_mob_prototype") as m_fin:
            self.script._spawn("orc", self.room)

        self.assertEqual(m_fin.call_count, 1)

    def test_get_room_caches_lookup(self):
        entry = {"room": "#1"}
        fake_room = mock.Mock(dbref="#1")
        fake_room.is_typeclass.return_value = True
        with mock.patch("scripts.spawn_manager.ObjectDB.objects.filter") as m_filter:
            m_filter.return_value.first.return_value = fake_room
            room1 = self.script._get_room(entry)
            room2 = self.script._get_room(entry)
        self.assertIs(room1, fake_room)
        self.assertIs(room2, fake_room)
        self.assertIs(entry["room"], fake_room)
        m_filter.assert_called_once()

    def test_batch_processing_spawns_by_tick(self):
        self.script.db.batch_size = 2
        self.script.db.tick_count = 0
        self.script.db.entries = [
            {
                "prototype": "a",
                "room": self.room,
                "room_id": 1,
                "max_count": 1,
                "respawn_rate": 5,
                "spawned": [],
                "dead_timestamps": [],
            },
            {
                "prototype": "b",
                "room": self.room,
                "room_id": 2,
                "max_count": 1,
                "respawn_rate": 5,
                "spawned": [],
                "dead_timestamps": [],
            },
        ]
        with mock.patch.object(self.script, "_spawn") as m_spawn, \
             mock.patch("scripts.spawn_manager.time.time", return_value=10), \
             mock.patch("evennia.utils.logger.log_debug") as m_debug:
            self.script.at_repeat()
            m_spawn.assert_called_once()
            m_debug.assert_called_once()

        m_spawn.reset_mock()
        with mock.patch.object(self.script, "_spawn", m_spawn), \
             mock.patch("scripts.spawn_manager.time.time", return_value=10), \
             mock.patch("evennia.utils.logger.log_debug") as m_debug:
            self.script.at_repeat()
            m_spawn.assert_called_once()
            m_debug.assert_called_once()

    def test_get_room_falls_back_to_room_id_when_dbref_not_room(self):
        dummy = create_object("typeclasses.objects.Object", key="dummy")
        self.script.db.entries = [
            {
                "area": "testarea",
                "prototype": "basic_merchant",
                "room": f"#{dummy.id}",
                "room_id": 1,
                "max_count": 1,
                "respawn_rate": 5,
                "spawned": [],
                "dead_timestamps": [],
            }
        ]
        npc = create_object(BaseNPC, key="basic_merchant")
        with mock.patch(
            "scripts.spawn_manager.prototypes.get_npc_prototypes",
            return_value={"basic_merchant": {"key": "basic_merchant"}},
        ), mock.patch("evennia.prototypes.spawner.spawn", return_value=[npc]):
            self.script.force_respawn(1)

        self.assertEqual(npc.location, self.room)

    def test_get_room_ignores_nonroom_search_result(self):
        entry = {"room": "fake"}
        fake_obj = mock.Mock()
        fake_obj.is_typeclass.return_value = False
        with mock.patch(
            "scripts.spawn_manager.search.search_object",
            return_value=[fake_obj],
        ):
            room = self.script._get_room(entry)
        self.assertIsNone(room)
        self.assertEqual(entry["room"], "fake")

    def test_force_respawn_handles_string_room_and_proto(self):
        self.script.db.entries = [
            {
                "area": "testarea",
                "prototype": "5",
                "room": "1",
                "room_id": 1,
                "max_count": 1,
                "respawn_rate": 5,
                "spawned": [],
                "dead_timestamps": [],
            }
        ]
        npc = create_object(BaseNPC, key="num")
        with mock.patch("scripts.spawn_manager.spawn_from_vnum") as m_spawn:
            def side(vnum, location=None):
                npc.location = location
                return npc

            m_spawn.side_effect = side
            self.script.force_respawn(1)

        self.assertEqual(npc.location, self.room)
        m_spawn.assert_called_once_with(5, location=self.room)

    def test_spawn_numeric_missing_proto_logs_details(self):
        with mock.patch("world.scripts.mob_db.get_mobdb") as m_db, \
             mock.patch("scripts.spawn_manager.prototypes.get_npc_prototypes", return_value={}), \
             mock.patch("evennia.utils.logger.log_warn") as m_warn:
            fake_db = mock.Mock()
            fake_db.get_proto.return_value = None
            m_db.return_value = fake_db

            self.script._spawn(5, self.room)

        m_warn.assert_called_once()
        msg = m_warn.call_args[0][0]
        self.assertIn("5", msg)
        self.assertIn(str(self.room.db.room_id), msg)
        self.assertIn("MobDB", msg)
        self.assertIn("JSON", msg)

    def test_spawn_key_missing_proto_logs_source(self):
        with mock.patch("scripts.spawn_manager.prototypes.get_npc_prototypes", return_value={}), \
             mock.patch("evennia.utils.logger.log_warn") as m_warn:
            self.script._spawn("orc", self.room)

        m_warn.assert_called_once()
        msg = m_warn.call_args[0][0]
        self.assertIn("orc", msg)
        self.assertIn(str(self.room.db.room_id), msg)
        self.assertIn("JSON registry", msg)

    def test_spawn_exception_logs_details(self):
        with mock.patch("world.scripts.mob_db.get_mobdb") as m_db, \
             mock.patch("scripts.spawn_manager.spawn_from_vnum") as m_spawn, \
             mock.patch("evennia.utils.logger.log_err") as m_err:
            fake_db = mock.Mock()
            fake_db.get_proto.return_value = {"key": "x"}
            m_db.return_value = fake_db
            m_spawn.side_effect = RuntimeError("boom")

            self.script._spawn(5, self.room)

        m_err.assert_called_once()
        msg = m_err.call_args[0][0]
        self.assertIn("5", msg)
        self.assertIn(str(self.room.db.room_id), msg)
        self.assertIn("boom", msg)

    def test_npc_on_death_falls_back_to_location(self):
        npc = create_object(BaseNPC, key="mob", location=self.room)
        npc.db.prototype_key = "goblin"
        with mock.patch("world.mechanics.on_death_manager.handle_death"), \
             mock.patch("utils.script_utils.get_spawn_manager", return_value=self.script), \
             mock.patch.object(self.script, "record_death") as mock_record:
            npc.on_death(self.char1)

        mock_record.assert_called_with("goblin", self.room, npc_id=npc.id)

