from unittest.mock import patch
from evennia.utils.test_resources import EvenniaTest
from evennia import create_object

from typeclasses.npcs import BaseNPC
from scripts.spawn_manager import SpawnManager
from world.area_reset import AreaReset
from world.areas import Area


class TestSpawnManager(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.script = SpawnManager()
        self.script.at_script_creation()
        self.room_proto = {
            "vnum": self.room1.db.room_id,
            "area": "zone",
            "spawns": [
                {
                    "prototype": "goblin",
                    "max_spawns": 3,
                    "spawn_interval": 5,
                    "location": f"#{self.room1.db.room_id}",
                }
            ],
        }

    def _fake_spawn(self, proto):
        npc = create_object(BaseNPC, key=proto["key"], location=self.room1)
        return [npc]

    def test_initial_spawn_from_metadata(self):
        with patch("evennia.prototypes.spawner.spawn", side_effect=self._fake_spawn), patch(
            "evennia.utils.delay", lambda t, func, *a, **kw: None
        ):
            self.script.register_room_spawn(self.room_proto)
            self.script.at_start()
        npcs = [o for o in self.room1.contents if o.key == "goblin"]
        self.assertEqual(len(npcs), 2)

    def test_at_start_only_spawns_missing(self):
        with patch("evennia.prototypes.spawner.spawn", side_effect=self._fake_spawn), patch(
            "evennia.utils.delay", lambda t, func, *a, **kw: None
        ):
            self.script.register_room_spawn(self.room_proto)
            npc = create_object(BaseNPC, key="goblin", location=self.room1)
            npc.db.prototype_key = "goblin"
            npc.db.spawn_room = self.room1
            self.script.at_start()
        npcs = [o for o in self.room1.contents if o.key == "goblin"]
        self.assertEqual(len(npcs), 2)

    def test_respawn_after_removal(self):
        with patch("evennia.prototypes.spawner.spawn", side_effect=self._fake_spawn), patch(
            "evennia.utils.delay", lambda t, func, *a, **kw: None
        ):
            self.script.register_room_spawn(self.room_proto)
            self.script.at_start()
            entry = self.script.db.entries[0]
            proto = entry["prototype"]
            npc = create_object(BaseNPC, key=proto, location=self.room1)
            npc.db.prototype_key = proto
            npc.db.spawn_room = self.room1
            # simulate removal
            npc.delete()
            self.script.force_respawn(self.room1.db.room_id)
        npcs = [o for o in self.room1.contents if o.key == "goblin"]
        self.assertEqual(len(npcs), 3)

    def test_area_reset_triggers_repopulate(self):
        area = Area(key="zone", start=1, end=10, reset_interval=1)
        with patch("evennia.prototypes.spawner.spawn", side_effect=self._fake_spawn), patch(
            "evennia.utils.delay", lambda t, func, *a, **kw: None
        ):
            self.script.register_room_spawn(self.room_proto)
            self.script.at_start()
        for npc in list(self.room1.contents):
            npc.delete()
            self.script.force_respawn(self.room1.db.room_id)
        script = AreaReset()
        script.at_script_creation()

        def update_side(idx, area_obj):
            if area_obj.age == 0:
                self.script.force_respawn(self.room1.db.room_id)

        with patch("world.area_reset.get_areas", return_value=[area]), patch(
            "world.area_reset.update_area", side_effect=update_side
        ):
            script.at_repeat()
            script.at_repeat()
        npcs = [o for o in self.room1.contents if o.key == "goblin"]
        self.assertEqual(len(npcs), 3)

    def test_register_twice_keeps_single_entry(self):
        self.script.register_room_spawn(self.room_proto)
        self.script.register_room_spawn(self.room_proto)
        self.assertEqual(len(self.script.db.entries), 1)

    def test_register_room_spawn_with_no_spawns_removes_entries(self):
        self.script.register_room_spawn(self.room_proto)
        self.assertEqual(len(self.script.db.entries), 1)
        proto = {"vnum": self.room1.db.room_id, "area": "zone", "spawns": []}
        self.script.register_room_spawn(proto)
        self.assertEqual(len(self.script.db.entries), 0)

    def test_periodic_spawn_interval(self):
        proto = {
            "vnum": self.room1.db.room_id,
            "area": "zone",
            "spawns": [
                {
                    "prototype": "goblin",
                    "max_spawns": 2,
                    "spawn_interval": 5,
                    "location": f"#{self.room1.db.room_id}",
                }
            ],
        }
        with patch("evennia.prototypes.spawner.spawn", side_effect=self._fake_spawn), patch(
            "evennia.utils.delay",
            lambda t, func, *a, **kw: None,
        ), patch(
            "world.prototypes.get_npc_prototypes",
            return_value={"goblin": {"key": "goblin"}},
        ):
            with patch("scripts.spawn_manager.time.time", return_value=1000):
                self.script.register_room_spawn(proto)
                self.script.at_start()

            npc = [o for o in self.room1.contents if o.key == "goblin"][0]
            npc.delete()

            # interval not reached, no spawn
            with patch("scripts.spawn_manager.time.time", return_value=1003):
                self.script.at_repeat()
            self.assertEqual(len([o for o in self.room1.contents if o.key == "goblin"]), 1)

            # interval reached, should spawn one
            with patch("scripts.spawn_manager.time.time", return_value=1006):
                self.script.at_repeat()
            self.assertEqual(len([o for o in self.room1.contents if o.key == "goblin"]), 2)

            # not enough time since last spawn
            with patch("scripts.spawn_manager.time.time", return_value=1007):
                self.script.at_repeat()
            self.assertEqual(len([o for o in self.room1.contents if o.key == "goblin"]), 2)
