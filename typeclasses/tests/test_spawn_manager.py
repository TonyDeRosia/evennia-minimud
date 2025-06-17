from unittest.mock import patch
from evennia.utils.test_resources import EvenniaTest
from evennia import create_object

from typeclasses.npcs import BaseNPC
from world.spawn_manager import SpawnManager
from world.area_reset import AreaReset
from world.areas import Area


class TestSpawnManager(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.manager = SpawnManager.get()
        self.manager.reset()
        self.proto = {
            "key": "goblin",
            "area": "zone",
            "typeclass": "typeclasses.npcs.BaseNPC",
            "metadata": {
                "spawn": {
                    "room": self.room1,
                    "initial_count": 2,
                    "max_count": 3,
                    "respawn_rate": 5,
                }
            },
        }

    def _fake_spawn(self, proto):
        npc = create_object(BaseNPC, key=proto["key"], location=self.room1)
        return [npc]

    def test_initial_spawn_from_metadata(self):
        with patch("evennia.prototypes.spawner.spawn", side_effect=self._fake_spawn), patch(
            "evennia.utils.delay", lambda t, func, *a, **kw: None
        ):
            self.manager.register_prototype(self.proto)
            self.manager.start()
        npcs = [o for o in self.room1.contents if o.key == "goblin"]
        self.assertEqual(len(npcs), 2)

    def test_respawn_after_removal(self):
        with patch("evennia.prototypes.spawner.spawn", side_effect=self._fake_spawn), patch(
            "evennia.utils.delay", lambda t, func, *a, **kw: None
        ):
            self.manager.register_prototype(self.proto)
            self.manager.start()
            entry = self.manager.entries[0]
            npc = entry.npcs.pop()
            npc.delete()
            self.manager.notify_removed(npc)
            # manually trigger check
            self.manager._check_entry(entry)
        npcs = [o for o in self.room1.contents if o.key == "goblin"]
        self.assertEqual(len(npcs), 3)

    def test_area_reset_triggers_repopulate(self):
        area = Area(key="zone", start=1, end=10, reset_interval=1)
        with patch("evennia.prototypes.spawner.spawn", side_effect=self._fake_spawn), patch(
            "evennia.utils.delay", lambda t, func, *a, **kw: None
        ):
            self.manager.register_prototype(self.proto)
            self.manager.start()
        for npc in list(self.room1.contents):
            npc.delete()
            self.manager.notify_removed(npc)
        script = AreaReset()
        script.at_script_creation()

        def update_side(idx, area_obj):
            if area_obj.age == 0:
                self.manager.repopulate_area(area_obj.key)

        with patch("world.area_reset.get_areas", return_value=[area]), patch(
            "world.area_reset.update_area", side_effect=update_side
        ):
            script.at_repeat()
            script.at_repeat()
        npcs = [o for o in self.room1.contents if o.key == "goblin"]
        self.assertEqual(len(npcs), 3)
