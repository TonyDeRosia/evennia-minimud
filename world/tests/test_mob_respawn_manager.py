import unittest
from unittest.mock import patch

from evennia.utils.test_resources import EvenniaTest
from evennia import create_object
from evennia.utils import create

from typeclasses.rooms import Room
from typeclasses.npcs import BaseNPC
from scripts.mob_respawn_manager import MobRespawnManager


class TestMobRespawnManager(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.script = create.create_script(MobRespawnManager, key="mob_respawn_manager")

    def _spawn_entry(self, room, proto="goblin", rate=5, max_count=1):
        proto_data = {
            "vnum": room.db.room_id,
            "area": room.db.area,
            "spawns": [
                {
                    "prototype": proto,
                    "max_spawns": max_count,
                    "spawn_interval": rate,
                }
            ],
        }
        self.script.register_room_spawn(proto_data)

    def test_rooms_grouped_by_area(self):
        room1 = create_object(Room, key="R1")
        room1.set_area("zone", 1)
        room2 = create_object(Room, key="R2")
        room2.set_area("zone", 2)
        room3 = create_object(Room, key="R3")
        room3.set_area("other", 3)
        self._spawn_entry(room1)
        self._spawn_entry(room2)
        self._spawn_entry(room3)

        with patch("scripts.mob_respawn_manager.MobRespawnTracker.process") as mock_proc:
            self.script.at_repeat()

        tracker_zone = self.script.db.trackers["zone"]
        tracker_other = self.script.db.trackers["other"]
        assert set(tracker_zone.rooms.keys()) == {1, 2}
        assert set(tracker_other.rooms.keys()) == {3}
        assert mock_proc.call_count == 2

    def test_dead_mob_respawns_after_rate(self):
        room = create_object(Room, key="R")
        room.set_area("zone", 1)
        self._spawn_entry(room, rate=5)

        npc = create_object(BaseNPC, key="orc")
        with patch.object(self.script, "_spawn", return_value=npc) as mock_spawn:
            with patch("scripts.mob_respawn_manager.time.time", return_value=0):
                self.script.force_respawn(room.db.room_id)
        assert npc.location == room

        npc.delete()
        with patch("scripts.mob_respawn_manager.time.time", return_value=1):
            self.script.record_death("orc", room, npc_id=npc.id)

        with patch.object(self.script, "_spawn", return_value=None) as mock_spawn:
            with patch("scripts.mob_respawn_manager.time.time", return_value=3):
                self.script.at_repeat()
            mock_spawn.assert_not_called()

        new_npc = create_object(BaseNPC, key="orc")
        with patch.object(self.script, "_spawn", return_value=new_npc) as mock_spawn:
            with patch("scripts.mob_respawn_manager.time.time", return_value=6):
                self.script.at_repeat()
            mock_spawn.assert_called_once()
        assert new_npc.location == room

    def test_npc_on_death_updates_tracker(self):
        room = create_object(Room, key="R")
        room.set_area("zone", 1)
        self._spawn_entry(room)

        npc = create_object(BaseNPC, key="orc")
        with patch.object(self.script, "_spawn", return_value=npc):
            with patch("scripts.mob_respawn_manager.time.time", return_value=0):
                self.script.force_respawn(room.db.room_id)

        with patch("world.mechanics.on_death_manager.handle_death", return_value=None), \
             patch("utils.script_utils.get_respawn_manager", return_value=self.script), \
             patch.object(self.script, "record_death", wraps=self.script.record_death) as mock_rec, \
             patch("scripts.mob_respawn_manager.time.time", return_value=1):
            npc.on_death(self.char1)

        mock_rec.assert_called_once_with(npc.db.prototype_key, room, npc_id=npc.id)
        entry = room.db.spawn_entries[0]
        assert entry["active_mobs"] == []
        assert entry["dead_mobs"][0]["id"] == npc.id

