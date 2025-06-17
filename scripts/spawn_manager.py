from __future__ import annotations

import time
from typing import Any, Dict, List

from evennia.prototypes import spawner
from evennia.objects.models import ObjectDB
from evennia.utils import logger, search

from typeclasses.scripts import Script
from utils.mob_proto import apply_proto_items, spawn_from_vnum
from world import prototypes


class SpawnManager(Script):
    """Global manager for spawning NPCs from prototypes."""

    def at_script_creation(self):
        self.key = "spawn_manager"
        self.desc = "Handles mob respawning for rooms"
        self.interval = 15
        self.persistent = True
        self.db.entries = self.db.entries or []

    # ------------------------------------------------------------
    # public API
    # ------------------------------------------------------------
    def load_spawn_data(self):
        """Load spawn entries from room prototypes."""
        from utils.prototype_manager import load_all_prototypes

        self.db.entries = []
        room_protos = load_all_prototypes("room")
        for proto in room_protos.values():
            spawns = proto.get("spawns") or []
            room_id = proto.get("room_id") or proto.get("vnum")
            if not spawns or room_id is None:
                continue
            for entry in spawns:
                proto_key = (
                    entry.get("prototype")
                    or entry.get("proto")
                    or entry.get("vnum")
                )
                if proto_key is None:
                    continue
                self.db.entries.append(
                    {
                        "area": (proto.get("area") or "").lower(),
                        "prototype": proto_key,
                        "room": int(room_id),
                        "initial_count": int(entry.get("initial_count", 0)),
                        "max_count": int(entry.get("max_count", 1)),
                        "respawn_rate": int(entry.get("respawn_rate", 60)),
                        "last_spawn": 0.0,
                    }
                )

    def record_spawn(self, prototype: Any, room: Any) -> None:
        """Update the last spawn time for ``prototype`` in ``room``."""
        for entry in self.db.entries:
            if entry.get("prototype") == prototype and self._room_match(
                entry.get("room"), room
            ):
                entry["last_spawn"] = time.time()
                break

    def register_room_spawn(self, proto: Dict[str, Any]) -> None:
        """Register spawn data from a single room prototype."""
        spawns = proto.get("spawns") or []
        room_id = proto.get("room_id") or proto.get("vnum")
        if room_id is None:
            return
        for entry in spawns:
            proto_key = (
                entry.get("prototype")
                or entry.get("proto")
                or entry.get("vnum")
            )
            if proto_key is None:
                continue
            data = {
                "area": (proto.get("area") or "").lower(),
                "prototype": proto_key,
                "room": int(room_id),
                "initial_count": int(entry.get("initial_count", 0)),
                "max_count": int(entry.get("max_count", 1)),
                "respawn_rate": int(entry.get("respawn_rate", 60)),
                "last_spawn": 0.0,
            }
            self.db.entries.append(data)

    def force_respawn(self, room_vnum: int) -> None:
        """Immediately respawn all entries for ``room_vnum``."""
        now = time.time()
        for entry in self.db.entries:
            rid = entry.get("room")
            if isinstance(rid, str) and rid.isdigit():
                rid = int(rid)
            if rid != room_vnum:
                continue
            room = self._get_room(entry)
            if not room:
                continue
            proto = entry.get("prototype")
            count = self._live_count(proto, room)
            missing = max(0, entry.get("max_count", 0) - count)
            if missing <= 0:
                logger.log_info(
                    f"SpawnManager: room {room_vnum} at max population for {proto}"
                )
                continue
            for _ in range(missing):
                self._spawn(proto, room)
            entry["last_spawn"] = now

    def reload_spawns(self) -> None:
        """Reload spawn data from prototypes and spawn initial mobs."""
        self.load_spawn_data()
        self.at_start()

    # ------------------------------------------------------------
    # internal helpers
    # ------------------------------------------------------------
    def _room_match(self, stored: Any, room: Any) -> bool:
        if hasattr(stored, "dbref"):
            return stored == room
        rid = None
        if isinstance(stored, int):
            rid = stored
        elif isinstance(stored, str) and stored.isdigit():
            rid = int(stored)
        if rid is not None:
            return getattr(room.db, "room_id", None) == rid
        return False

    def _get_room(self, entry: Dict) -> Any | None:
        room = entry.get("room")
        if hasattr(room, "dbref"):
            return room
        rid = None
        if isinstance(room, int):
            rid = room
        elif isinstance(room, str) and room.isdigit():
            rid = int(room)
        if rid is not None:
            objs = ObjectDB.objects.get_by_attribute(key="room_id", value=rid)
            return objs[0] if objs else None
        objs = search.search_object(room)
        return objs[0] if objs else None

    def _live_count(self, proto: Any, room: Any) -> int:
        return len(
            [
                obj
                for obj in room.contents
                if obj.db.prototype_key == proto and obj.db.spawn_room == room
            ]
        )

    def _spawn(self, proto: Any, room: Any) -> None:
        npc = None
        try:
            if isinstance(proto, int) or (isinstance(proto, str) and str(proto).isdigit()):
                npc = spawn_from_vnum(int(proto), location=room)
                npc.db.prototype_key = int(proto)
            else:
                p_data = prototypes.get_npc_prototypes().get(str(proto))
                if not p_data:
                    return
                data = dict(p_data)
                base_cls = data.get("typeclass", "typeclasses.npcs.BaseNPC")
                if isinstance(base_cls, str):
                    module, clsname = base_cls.rsplit(".", 1)
                    base_cls = getattr(__import__(module, fromlist=[clsname]), clsname)
                data["typeclass"] = base_cls
                npc = spawner.spawn(data)[0]
                npc.location = room
                npc.db.prototype_key = proto
                apply_proto_items(npc, data)
        except Exception as err:  # pragma: no cover - log errors
            logger.log_err(f"SpawnManager error spawning {proto}: {err}")
            return

        if npc:
            npc.db.spawn_room = room
            npc.db.area_tag = room.db.area
            try:
                from commands.npc_builder import finalize_mob_prototype  # lazy import
                finalize_mob_prototype(npc, npc)
            except Exception as err:  # pragma: no cover - log errors
                logger.log_err(f"Finalize error on {npc}: {err}")

    # ------------------------------------------------------------
    # script hooks
    # ------------------------------------------------------------
    def at_start(self):
        for entry in self.db.entries:
            room = self._get_room(entry)
            if not room:
                continue
            for _ in range(entry.get("initial_count", 0)):
                if self._live_count(entry.get("prototype"), room) < entry.get("max_count", 0):
                    self._spawn(entry.get("prototype"), room)
                    entry["last_spawn"] = time.time()
                    logger.log_info(
                        f"SpawnManager: spawned {entry.get('prototype')} in room {room.dbref}"
                    )

    def at_repeat(self):
        now = time.time()
        for entry in self.db.entries:
            room = self._get_room(entry)
            if not room:
                continue
            proto = entry.get("prototype")
            live = self._live_count(proto, room)
            if live >= entry.get("max_count", 0):
                logger.log_info(
                    f"SpawnManager: limit reached in room {room.dbref} for {proto}"
                )
                continue
            last = entry.get("last_spawn", 0)
            if now - last >= entry.get("respawn_rate", self.interval):
                self._spawn(proto, room)
                entry["last_spawn"] = now
                logger.log_info(
                    f"SpawnManager: spawned {proto} in room {room.dbref}"
                )

