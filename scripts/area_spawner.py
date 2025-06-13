"""Script for repopulating NPCs in a zone."""

from random import choice, randint

from evennia.prototypes import spawner
from utils.mob_proto import spawn_from_vnum, apply_proto_items
from evennia.utils import logger
from commands.npc_builder import finalize_mob_prototype
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
        if proto_key.isdigit():
            try:
                npc = spawn_from_vnum(int(proto_key), location=room)
            except ValueError as err:
                logger.log_err(str(err))
                return
        else:
            proto = prototypes.get_npc_prototypes().get(proto_key)
            if not proto:
                return
            proto_data = dict(proto)
            base_cls = proto_data.get("typeclass", "typeclasses.npcs.BaseNPC")
            if isinstance(base_cls, str):
                module, clsname = base_cls.rsplit(".", 1)
                base_cls = getattr(__import__(module, fromlist=[clsname]), clsname)

            from typeclasses.characters import NPC

            if not issubclass(base_cls, NPC):
                logger.log_warn(
                    f"Prototype {proto_key}: {base_cls} is not a subclass of NPC; using BaseNPC."
                )
                from typeclasses.npcs import BaseNPC as DefaultNPC

                base_cls = DefaultNPC

            proto_data["typeclass"] = base_cls
            npc = spawner.spawn(proto_data)[0]
            npc.location = room
            npc.db.prototype_key = proto_key
            apply_proto_items(npc, proto_data)
        finalize_mob_prototype(npc, npc)
        npc.db.area_tag = area
        npc.db.spawn_room = room
