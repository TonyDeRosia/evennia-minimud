from __future__ import annotations

"""Simple spawn management for area resets."""

from dataclasses import dataclass, asdict
from typing import List, Dict

from evennia.server.models import ServerConfig
from evennia.objects.models import ObjectDB
from evennia.prototypes import spawner
from evennia.utils import logger

from world import prototypes
from utils.mob_proto import spawn_from_vnum, apply_proto_items
from commands.npc_builder import finalize_mob_prototype
from typeclasses.npcs import BaseNPC


@dataclass
class SpawnEntry:
    """Data container representing a spawn entry."""

    area: str
    proto: str
    room: int
    initial_count: int = 1
    max_count: int = 1

    @classmethod
    def from_dict(cls, data: Dict) -> "SpawnEntry":
        return cls(
            area=data.get("area", "").lower(),
            proto=str(data.get("proto", "")),
            room=int(data.get("room", 0)),
            initial_count=int(data.get("initial_count", 1)),
            max_count=int(data.get("max_count", 1)),
        )

    def to_dict(self) -> Dict:
        return asdict(self)


_REGISTRY_KEY = "spawn_registry"


class SpawnManager:
    """Utility class for accessing spawn entries."""

    @staticmethod
    def _load_registry() -> List[Dict]:
        return ServerConfig.objects.conf(_REGISTRY_KEY, default=list)

    @staticmethod
    def _save_registry(registry: List[Dict]):
        ServerConfig.objects.conf(_REGISTRY_KEY, value=registry)

    @staticmethod
    def get_entries(area: str | None = None) -> List[SpawnEntry]:
        entries = [SpawnEntry.from_dict(d) for d in SpawnManager._load_registry()]
        if area:
            area = area.lower()
            entries = [e for e in entries if e.area.lower() == area]
        return entries

    @staticmethod
    def reset_area(area_key: str) -> None:
        """Repopulate all spawn entries for ``area_key``."""

        area = area_key.lower()
        entries = SpawnManager.get_entries(area)
        if not entries:
            return

        for entry in entries:
            room = None
            objs = ObjectDB.objects.filter(
                db_attributes__db_key="area",
                db_attributes__db_strvalue__iexact=entry.area,
            )
            for obj in objs:
                if obj.db.room_id == entry.room and obj.is_typeclass(
                    "typeclasses.rooms.Room", exact=False
                ):
                    room = obj
                    break
            if not room:
                continue

            existing = [
                obj
                for obj in room.contents
                if obj.is_typeclass(BaseNPC, exact=False)
                and str(obj.db.prototype_key or obj.db.vnum or "") == entry.proto
            ]
            to_spawn = entry.initial_count - len(existing)
            if to_spawn <= 0:
                continue
            to_spawn = min(to_spawn, entry.max_count - len(existing))
            for _ in range(to_spawn):
                npc = None
                if entry.proto.isdigit():
                    try:
                        npc = spawn_from_vnum(int(entry.proto), location=room)
                    except ValueError as err:
                        logger.log_err(str(err))
                        continue
                else:
                    proto = prototypes.get_npc_prototypes().get(entry.proto)
                    if not proto:
                        continue
                    proto_data = dict(proto)
                    base_cls = proto_data.get("typeclass", "typeclasses.npcs.BaseNPC")
                    if isinstance(base_cls, str):
                        module, clsname = base_cls.rsplit(".", 1)
                        base_cls = getattr(__import__(module, fromlist=[clsname]), clsname)

                    from typeclasses.characters import NPC as BaseChar

                    if not issubclass(base_cls, BaseChar):
                        logger.log_warn(
                            f"Prototype {entry.proto}: {base_cls} is not a subclass of NPC; using BaseNPC."
                        )
                        from typeclasses.npcs import BaseNPC as DefaultNPC

                        base_cls = DefaultNPC

                    proto_data["typeclass"] = base_cls
                    npc = spawner.spawn(proto_data)[0]
                    npc.location = room
                    npc.db.prototype_key = entry.proto
                    apply_proto_items(npc, proto_data)
                finalize_mob_prototype(npc, npc)
                npc.db.area_tag = entry.area
                npc.db.spawn_room = room
