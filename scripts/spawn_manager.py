
"""Global NPC spawning manager.

This script loads room spawn definitions from prototype files and handles
timed respawning of NPCs. It runs as a single persistent script started at
server boot via ``at_server_start`` and keeps track of what NPCs should exist
in each room.

Commands interacting with this manager include ``@spawnreload`` to reload all
spawn entries, ``@forcerespawn`` for immediate checks, ``@showspawns`` to view
configured spawns, ``@resetworld`` to repopulate all areas and ``areas.reset``
for individual areas. Saving room spawns through ``redit`` automatically
registers them with the manager as well.
"""

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
        self.interval = 60
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
            if not spawns:
                continue
            for entry in spawns:
                proto_key = entry.get("prototype") or entry.get("proto")
                if not proto_key:
                    continue
                room_loc = entry.get("location") or proto.get("vnum") or proto.get("room_id")
                data = {
                    "area": (proto.get("area") or "").lower(),
                    "prototype": proto_key,
                    "room": room_loc,
                    "max_count": int(entry.get("max_spawns", entry.get("max_count", 1))),
                    "respawn_rate": int(entry.get("spawn_interval", entry.get("respawn_rate", 60))),
                    "last_spawn": 0.0,
                }
                self.db.entries.append(data)

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
        if not spawns:
            return
        room_id = proto.get("room_id") or proto.get("vnum")
        rid = (
            int(room_id)
            if isinstance(room_id, str) and room_id.isdigit()
            else room_id
        )
        self.db.entries = [
            e
            for e in self.db.entries
            if self._normalize_room_id(e.get("room")) != rid
        ]
        for entry in spawns:
            proto_key = entry.get("prototype") or entry.get("proto")
            if not proto_key:
                continue
            data = {
                "area": (proto.get("area") or "").lower(),
                "prototype": proto_key,
                "room": entry.get("location") or room_id,
                "max_count": int(entry.get("max_spawns", entry.get("max_count", 1))),
                "respawn_rate": int(entry.get("spawn_interval", entry.get("respawn_rate", 60))),
                "last_spawn": 0.0,
            }
            self.db.entries.append(data)

    def force_respawn(self, room_vnum: int) -> None:
        """Immediately respawn all entries for ``room_vnum``."""
        now = time.time()
        for entry in self.db.entries:
            if self._normalize_room_id(entry.get("room")) != room_vnum:
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
        # Force an immediate respawn in every room after reloading. This helps
        # during debugging so changes to prototypes are reflected right away.
        for entry in self.db.entries:
            room_vnum = self._normalize_room_id(entry.get("room"))
            if room_vnum is not None:
                self.force_respawn(room_vnum)

    # ------------------------------------------------------------
    # internal helpers
    # ------------------------------------------------------------
    def _normalize_room_id(self, room: Any) -> int | None:
        if hasattr(room, "dbref"):
            return getattr(room.db, "room_id", None)
        if isinstance(room, int):
            return room
        if isinstance(room, str):
            if room.startswith("#") and room[1:].isdigit():
                return int(room[1:])
            if room.isdigit():
                return int(room)
        return None

    def _room_match(self, stored: Any, room: Any) -> bool:
        if hasattr(stored, "dbref"):
            return stored == room
        rid = None
        if isinstance(stored, int):
            rid = stored
        elif isinstance(stored, str):
            if stored.startswith("#") and stored[1:].isdigit():
                rid = int(stored[1:])
            elif stored.isdigit():
                rid = int(stored)
        if rid is not None:
            return room.id == rid or getattr(room.db, "room_id", None) == rid
        return False

    def _get_room(self, entry: Dict) -> Any | None:
        room = entry.get("room")
        if hasattr(room, "dbref"):
            return room
        rid = None
        if isinstance(room, int):
            rid = room
        elif isinstance(room, str):
            if room.startswith("#") and room[1:].isdigit():
                obj = ObjectDB.objects.filter(id=int(room[1:])).first()
                if obj:
                    return obj
                rid = int(room[1:])
            elif room.isdigit():
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
                    logger.log_warn(
                        f"SpawnManager: prototype {proto} not found for room {getattr(room, 'dbref', room)}"
                    )
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
            proto = entry.get("prototype")
            if not room:
                logger.log_warn(
                    f"SpawnManager: room {entry.get('room')} not found for {proto}"
                )
                continue
            existing = self._live_count(proto, room)
            max_count = entry.get("max_count", 1)
            if existing >= max_count:
                logger.log_info(
                    f"SpawnManager: skipping spawn in room {room.dbref} for {proto}; capacity {existing}/{max_count}"
                )
                continue
            to_spawn = max(0, max_count - existing)
            for _ in range(to_spawn):
                if self._live_count(proto, room) < max_count:
                    self._spawn(proto, room)
                    entry["last_spawn"] = time.time()
                    logger.log_info(
                        f"SpawnManager: spawned {proto} in room {room.dbref}"
                    )

    def at_repeat(self):
        now = time.time()
        for entry in self.db.entries:
            room = self._get_room(entry)
            proto = entry.get("prototype")
            if not room:
                logger.log_warn(
                    f"SpawnManager: room {entry.get('room')} not found for {proto}"
                )
                continue
            live = self._live_count(proto, room)
            max_count = entry.get("max_count", 0)
            if live >= max_count:
                logger.log_info(
                    f"SpawnManager: skipping spawn in room {room.dbref} for {proto}; capacity {live}/{max_count}"
                )
                continue
            last = entry.get("last_spawn", 0)
            if now - last >= entry.get("respawn_rate", self.interval):
                self._spawn(proto, room)
                entry["last_spawn"] = now
                logger.log_info(
                    f"SpawnManager: spawned {proto} in room {room.dbref}"
                )

