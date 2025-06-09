"""Script for repopulating NPCs in a zone."""

from random import choice, randint

from evennia.prototypes import spawner
from typeclasses.scripts import Script
from typeclasses.npcs import BaseNPC
from world import area_npcs, prototypes


class AreaSpawner(Script):
    """Respawn NPCs for an area on a timer."""

    def at_script_creation(self):
        self.key = "area_spawner"
        self.desc = "Handles NPC respawning for this room"
        self.interval = self.db.respawn_interval or 300
        self.persistent = True
        self.db.respawn_interval = self.interval
        self.db.max_population = self.db.max_population or 5
        self.db.spawn_chance = self.db.spawn_chance if self.db.spawn_chance is not None else 100

    def at_repeat(self):
        room = self.obj
        if not room:
            return
        area = room.db.area
        if not area:
            return
        proto_keys = area_npcs.get_area_npc_list(area)
        if not proto_keys:
            return

        npcs = [obj for obj in room.contents if obj.is_typeclass(BaseNPC, exact=False)]
        if len(npcs) >= self.db.max_population:
            return
        if randint(1, 100) > self.db.spawn_chance:
            return

        proto_key = choice(proto_keys)
        proto = prototypes.get_npc_prototypes().get(proto_key)
        if not proto:
            return
        npc = spawner.spawn(proto)[0]
        npc.location = room
        npc.db.prototype_key = proto_key
        npc.db.area_tag = area
        npc.db.spawn_room = room
