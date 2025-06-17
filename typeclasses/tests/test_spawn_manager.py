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
                    "initial_count": 2,
                    "max_count": 3,
                    "respawn_rate": 5,
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
