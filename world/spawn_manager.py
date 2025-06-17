from __future__ import annotations

"""Simple NPC spawn manager for tests."""

from dataclasses import dataclass, field
from typing import List, Dict, Any

from evennia.prototypes import spawner
from evennia.utils import delay


@dataclass
class SpawnEntry:
    proto: Dict[str, Any]
    area: str
    room: Any
    initial_count: int
    max_count: int
    respawn_rate: int
    npcs: List[Any] = field(default_factory=list)


class SpawnManager:
    """Manage spawning of NPCs from prototypes."""

    _instance: "SpawnManager" | None = None

    def __init__(self):
        self.entries: List[SpawnEntry] = []

    @classmethod
    def get(cls) -> "SpawnManager":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def reset(self):
        self.entries.clear()

    def register_prototype(self, proto: Dict[str, Any]):
        meta = proto.get("metadata", {}).get("spawn")
        if not meta:
            return
        entry = SpawnEntry(
            proto=proto,
            area=meta.get("area") or proto.get("area", ""),
            room=meta.get("room"),
            initial_count=int(meta.get("initial_count", 0)),
            max_count=int(meta.get("max_count", meta.get("initial_count", 0))),
            respawn_rate=int(meta.get("respawn_rate", 60)),
        )
        self.entries.append(entry)

    # ------------------------------------------------------------
    # lifecycle
    # ------------------------------------------------------------
    def start(self):
        for entry in self.entries:
            self._spawn_initial(entry)
            self._schedule(entry)

    def _spawn_initial(self, entry: SpawnEntry):
        for _ in range(entry.initial_count):
            npc = self._spawn(entry)
            entry.npcs.append(npc)

    def _spawn(self, entry: SpawnEntry):
        npc = spawner.spawn(entry.proto)[0]
        npc.location = entry.room
        npc.db.spawn_entry = entry
        return npc

    def _schedule(self, entry: SpawnEntry):
        delay(entry.respawn_rate, self._check_entry, entry)

    def _check_entry(self, entry: SpawnEntry):
        alive = [npc for npc in entry.npcs if npc.location == entry.room]
        entry.npcs = alive
        missing = entry.max_count - len(alive)
        for _ in range(missing):
            npc = self._spawn(entry)
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
        for entry in self.entries:
            if entry.area == area_key:
                for npc in list(entry.npcs):
                    try:
                        npc.delete()
                    except Exception:
                        pass
                entry.npcs.clear()
                for _ in range(entry.max_count):
                    npc = self._spawn(entry)
                    entry.npcs.append(npc)
