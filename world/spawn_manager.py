from __future__ import annotations

"""Spawn manager that supports persistent and live area-based mob spawning."""

from dataclasses import dataclass, asdict, field
from typing import List, Dict, Any

from evennia.server.models import ServerConfig
from evennia.objects.models import ObjectDB
from evennia.prototypes import spawner
from evennia.utils import logger, delay

from world import prototypes
from utils.mob_proto import spawn_from_vnum, apply_proto_items
from commands.npc_builder import finalize_mob_prototype
from typeclasses.npcs import BaseNPC


_REGISTRY_KEY = "spawn_registry"


@dataclass
class SpawnEntry:
    """Data container representing a mob spawn entry."""
    area: str
    proto: str
    room: int
    initial_count: int = 1
    max_count: int = 1
    respawn_rate: int = 300  # seconds
    npcs: List[Any] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict) -> "SpawnEntry":
        return cls(
            area=data.get("area", "").lower(),
            proto=str(data.get("proto", "")),
            room=int(data.get("room", 0)),
            initial_count=int(data.get("initial_count", 1)),
            max_count=int(data.get("max_count", 1)),
            respawn_rate=int(data.get("respawn_rate", 300)),
        )

    def to_dict(self) -> Dict:
        return asdict(self)


class SpawnManager:
    """Manages NPC spawning across areas."""

    _instance: SpawnManager | None = None

    def __init__(self):
        self.entries: List[SpawnEntry] = []

    @classmethod
    def get(cls) -> SpawnManager:
        if not cls._instance:
            cls._instance = cls()
        return cls._instance

    def reset(self):
        self.entries.clear()

    def register_prototype(self, proto: Dict[str, Any]):
        meta = proto.get("metadata", {}).get("spawn")
        if not meta:
            return
        entry = SpawnEntry(
            area=meta.get("area", "").lower(),
            proto=str(proto.get("prototype_key") or proto.get("vnum") or ""),
            room=meta.get("room", 0),
            initial_count=int(meta.get("initial_count", 1)),
            max_count=int(meta.get("max_count", 1)),
            respawn_rate=int(meta.get("respawn_rate", 300)),
        )
        self.entries.append(entry)

    def start(self):
        for entry in self.entries:
            self._spawn_initial(entry)
            self._schedule(entry)

    def _spawn_initial(self, entry: SpawnEntry):
        for _ in range(entry.initial_count):
            npc = self._spawn(entry)
            if npc:
                entry.npcs.append(npc)

    def _spawn(self, entry: SpawnEntry):
        room = self._find_room(entry)
        if not room:
            return None
        try:
            if entry.proto.isdigit():
                npc = spawn_from_vnum(int(entry.proto), location=room)
            else:
                proto = prototypes.get_npc_prototypes().get(entry.proto)
                if not proto:
                    return None
                proto_data = dict(proto)
                npc = spawner.spawn(proto_data)[0]
                npc.location = room
                npc.db.prototype_key = entry.proto
                apply_proto_items(npc, proto_data)
            finalize_mob_prototype(npc, npc)
            npc.db.area_tag = entry.area
            npc.db.spawn_room = room
            npc.db.spawn_entry = entry
            return npc
        except Exception as err:
            logger.log_err(f"Error spawning NPC from proto {entry.proto}: {err}")
            return None

    def _schedule(self, entry: SpawnEntry):
        delay(entry.respawn_rate, self._check_entry, entry)

    def _check_entry(self, entry: SpawnEntry):
        room = self._find_room(entry)
        if not room:
            return
        alive = [npc for npc in entry.npcs if npc.location == room]
        entry.npcs = alive
        missing = max(0, entry.max_count - len(alive))
        for _ in range(missing):
            npc = self._spawn(entry)
            if npc:
                entry.npcs.append(npc)
        self._schedule(entry)

    def notify_removed(self, npc):
        entry = getattr(npc.db, "spawn_entry", None)
        if not entry:
            return
        try:
            entry.npcs.remove(npc)
        except ValueError:
            pass

    def repopulate_area(self, area_key: str):
        area = area_key.lower()
        for entry in self.entries:
            if entry.area == area:
                for npc in list(entry.npcs):
                    try:
                        npc.delete()
                    except Exception:
                        pass
                entry.npcs.clear()
                for _ in range(entry.max_count):
                    npc = self._spawn(entry)
                    if npc:
                        entry.npcs.append(npc)

    def _find_room(self, entry: SpawnEntry):
        objs = ObjectDB.objects.filter(
            db_attributes__db_key="area",
            db_attributes__db_strvalue__iexact=entry.area,
        )
        for obj in objs:
            if obj.db.room_id == entry.room and obj.is_typeclass(
                "typeclasses.rooms.Room", exact=False
            ):
                return obj
        return None

    def load_registry(self):
        self.entries = [
            SpawnEntry.from_dict(d) for d in ServerConfig.objects.conf(_REGISTRY_KEY, default=list)
        ]

    def save_registry(self):
        ServerConfig.objects.conf(
            _REGISTRY_KEY,
            value=[entry.to_dict() for entry in self.entries]
        )

    # ------------------------------------------------------------------
    # class helpers for persistent registry access
    # ------------------------------------------------------------------

    @classmethod
    def _load_registry(cls) -> List[Dict]:
        """Return the stored spawn registry."""
        return ServerConfig.objects.conf(_REGISTRY_KEY, default=list)

    @classmethod
    def _save_registry(cls, registry: List[Dict]) -> None:
        """Persist ``registry`` to ServerConfig."""
        ServerConfig.objects.conf(_REGISTRY_KEY, value=registry)

    @classmethod
    def reset_area(cls, area_key: str) -> None:
        """Despawn and respawn all spawns for ``area_key``."""
        manager = cls.get()
        manager.entries = [SpawnEntry.from_dict(d) for d in cls._load_registry()]
        manager.repopulate_area(area_key)

    @classmethod
    def get_area_keys(cls) -> List[str]:
        """Return all unique area keys from registered spawns."""
        registry = cls._load_registry()
        return sorted({str(d.get("area", "")).lower() for d in registry if d.get("area")})

    @classmethod
    def reload_spawns(cls) -> None:
        """Reload spawn entries from NPC prototypes."""
        manager = cls.get()
        manager.entries.clear()
        from world import prototypes

        for proto in prototypes.get_npc_prototypes().values():
            spawn = proto.get("spawn") or {}
            if not spawn:
                continue

            room = spawn.get("room_vnum") or spawn.get("room")
            if room is None:
                continue

            entry = SpawnEntry(
                area=str(spawn.get("area", "")).lower(),
                proto=str(proto.get("vnum") or proto.get("key") or ""),
                room=int(room),
                initial_count=int(spawn.get("initial_count", 1)),
                max_count=int(spawn.get("max_count", 1)),
                respawn_rate=int(spawn.get("respawn_rate", 300)),
            )
            manager.entries.append(entry)

        cls._save_registry([e.to_dict() for e in manager.entries])

    @classmethod
    def force_respawn(cls, room_vnum: int) -> None:
        """Immediately run spawn checks for ``room_vnum``."""
        manager = cls.get()
        if not manager.entries:
            manager.entries = [SpawnEntry.from_dict(d) for d in cls._load_registry()]

        for entry in manager.entries:
            if entry.room == int(room_vnum):
                manager._check_entry(entry)
                break
