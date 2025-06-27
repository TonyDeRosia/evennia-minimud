from __future__ import annotations

import time
from typing import Any, Dict, List

from evennia.prototypes import spawner
from evennia.objects.models import ObjectDB
from evennia.utils import logger, search

if not hasattr(logger, "log_debug"):
    logger.log_debug = logger.log_info
from typeclasses.rooms import Room

from typeclasses.scripts import Script
from utils.mob_proto import apply_proto_items, spawn_from_vnum, load_npc_prototypes
from world import prototypes


class SpawnManager(Script):
    """Global manager for spawning NPCs from prototypes.

    Prototype identifiers may be provided as integers or numeric strings. The
    manager normalizes these using :meth:`_normalize_proto` so values like ``5``
    and ``"5"`` are treated the same when counting existing spawns or looking up
    prototypes.

    The respawn timer for an entry is based on the time of the last recorded
    death. :meth:`record_death` is called when an NPC dies to update this
    timestamp.
    """

    def at_script_creation(self):
        self.key = "spawn_manager"
        self.desc = "Handles mob respawning for rooms"
        # run frequently so short spawn intervals are respected
        self.interval = 5
        self.persistent = True
        self.repeats = -1
        self.start_delay = False
        self.db.entries = self.db.entries or []
        for entry in self.db.entries:
            entry.setdefault("spawned", [])
            entry.setdefault("dead_timestamps", [])
        self.db.batch_size = self.db.batch_size or 1
        self.db.tick_count = self.db.tick_count or 0

    # ------------------------------------------------------------
    # public API
    # ------------------------------------------------------------
    def load_spawn_data(self):
        from utils.prototype_manager import load_all_prototypes
        from world.scripts.mob_db import get_mobdb

        self.db.entries = []
        room_protos = load_all_prototypes("room")
        npc_registry = prototypes.get_npc_prototypes()
        mob_db = get_mobdb()
        for proto in room_protos.values():
            spawns = proto.get("spawns") or []
            if not spawns:
                continue
            for entry in spawns:
                proto_key = entry.get("prototype") or entry.get("proto")
                if not proto_key:
                    continue
                proto_key = self._normalize_proto(proto_key)
                if isinstance(proto_key, int):
                    if not mob_db.get_proto(proto_key):
                        if str(proto_key) in npc_registry:
                            logger.log_warn(
                                f"SpawnManager: NPC VNUM '{proto_key}' missing from MobDB; using registry prototype"
                            )
                        else:
                            logger.log_warn(
                                f"SpawnManager: missing NPC prototype '{proto_key}' for room spawn"
                            )
                            continue
                elif str(proto_key) not in npc_registry:
                    logger.log_warn(
                        f"SpawnManager: missing NPC prototype '{proto_key}' for room spawn"
                    )
                    continue

                room_loc = entry.get("location") or proto.get("vnum") or proto.get("room_id")
                rid = self._normalize_room_id(room_loc)
                self.db.entries.append(
                    {
                        "area": (proto.get("area") or "").lower(),
                        "prototype": proto_key,
                        "room": room_loc,
                        "room_id": rid,
                        "max_count": int(
                            entry.get("max_spawns", entry.get("max_count", 1))
                        ),
                        "respawn_rate": int(
                            entry.get("spawn_interval", entry.get("respawn_rate", 60))
                        ),
                        "spawned": [],
                        "dead_timestamps": [],
                        "last_spawn": 0.0,
                    }
                )

    def record_spawn(self, prototype: Any, room: Any, npc_id: int | None = None) -> None:
        """Record that ``prototype`` was spawned in ``room``.

        Parameters
        ----------
        prototype
            Prototype identifier.
        room
            Room where the NPC spawned.
        npc_id
            Optional database id of the spawned NPC.
        """

        norm = self._normalize_proto(prototype)
        for entry in self.db.entries:
            if self._normalize_proto(entry.get("prototype")) == norm and self._room_match(entry, room):
                entry.setdefault("spawned", [])
                if npc_id is not None:
                    if npc_id not in entry["spawned"]:
                        entry["spawned"].append(npc_id)
                entry["last_spawn"] = time.time()
                break

    def record_death(self, prototype: Any, room: Any, npc_id: int | None = None) -> None:
        """Record that ``prototype`` died in ``room``."""

        norm = self._normalize_proto(prototype)
        now = time.time()
        for entry in self.db.entries:
            if self._normalize_proto(entry.get("prototype")) == norm and self._room_match(entry, room):
                entry.setdefault("dead_timestamps", []).append(now)
                if npc_id is not None:
                    spawned = [sid for sid in entry.get("spawned", []) if sid != npc_id]
                    entry["spawned"] = spawned
                entry["last_spawn"] = now
                break

    def register_room_spawn(self, proto: Dict[str, Any]) -> None:
        spawns = proto.get("spawns") or []
        room_id = proto.get("room_id") or proto.get("vnum")
        rid = self._normalize_room_id(room_id)
        # always remove existing entries for this room to keep data in sync
        self.db.entries = [
            e for e in self.db.entries if self._normalize_room_id(e) != rid
        ]
        if not spawns:
            return
        for entry in spawns:
            proto_key = entry.get("prototype") or entry.get("proto")
            if not proto_key:
                continue
            proto_key = self._normalize_proto(proto_key)
            room_val = entry.get("location") or room_id
            self.db.entries.append(
                {
                    "area": (proto.get("area") or "").lower(),
                    "prototype": proto_key,
                    "room": room_val,
                    "room_id": self._normalize_room_id(room_val),
                    "max_count": int(
                        entry.get("max_spawns", entry.get("max_count", 1))
                    ),
                    "respawn_rate": int(
                        entry.get("spawn_interval", entry.get("respawn_rate", 60))
                    ),
                    "spawned": [],
                    "dead_timestamps": [],
                    "last_spawn": 0.0,
                }
            )

    def force_respawn(self, room_vnum: int) -> None:
        now = time.time()
        for entry in self.db.entries:
            if self._normalize_room_id(entry) != room_vnum:
                continue
            room = self._get_room(entry)
            if not room:
                continue
            proto = entry.get("prototype")
            count = self._live_count(proto, room)
            missing = max(0, entry.get("max_count", 0) - count)
            if missing <= 0:
                logger.log_info(f"SpawnManager: room {room_vnum} at max population for {proto}")
                continue
            for _ in range(missing):
                npc = self._spawn(proto, room)
                if npc:
                    entry.setdefault("spawned", []).append(npc.id)
            entry["last_spawn"] = now

    def reload_spawns(self) -> None:
        load_npc_prototypes()
        self.load_spawn_data()
        logger.log_info(
            f"SpawnManager: loaded {len(self.db.entries)} spawn entries"
        )
        self.at_start()
        for entry in self.db.entries:
            room_vnum = self._normalize_room_id(entry)
            if room_vnum is not None:
                self.force_respawn(room_vnum)

    # ------------------------------------------------------------
    # internal helpers
    # ------------------------------------------------------------
    def _normalize_room_id(self, room: Any) -> int | None:
        if isinstance(room, dict):
            if "room_id" in room:
                return room.get("room_id")
            room = room.get("room")
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

    def _normalize_proto(self, proto: Any) -> Any:
        """Return int(proto) if the prototype is numeric."""
        if isinstance(proto, int):
            return proto
        try:
            if str(proto).isdigit():
                return int(proto)
        except Exception:
            pass
        return proto

    def _room_match(self, stored: Any, room: Any) -> bool:
        if isinstance(stored, dict):
            rid = stored.get("room_id")
            stored = stored.get("room")
        else:
            rid = None
        if hasattr(stored, "dbref"):
            return stored == room
        if rid is None:
            rid = self._normalize_room_id(stored)
        if rid is not None:
            return room.id == rid or getattr(room.db, "room_id", None) == rid
        return False

    def _get_room(self, entry: Dict) -> Any | None:
        room = entry.get("room")
        if hasattr(room, "dbref"):
            return room
        rid = entry.get("room_id")
        if isinstance(room, str) and room.startswith("#") and room[1:].isdigit():
            obj = ObjectDB.objects.filter(id=int(room[1:])).first()
            if obj and obj.is_typeclass(Room, exact=False):
                entry["room"] = obj
                return obj
            if rid is None:
                rid = int(room[1:])
        elif rid is None:
            rid = self._normalize_room_id(room)
        if rid is not None:
            objs = ObjectDB.objects.get_by_attribute(key="room_id", value=rid)
            obj = objs[0] if objs else None
            if obj:
                entry["room"] = obj
            return obj
        objs = search.search_object(room)
        obj = objs[0] if objs else None
        if obj and obj.is_typeclass(Room, exact=False):
            entry["room"] = obj
            return obj
        return None

    def _live_count(self, proto: Any, room: Any) -> int:
        target = self._normalize_proto(proto)
        return len(
            [
                obj
                for obj in room.contents
                if self._normalize_proto(getattr(obj.db, "prototype_key", None)) == target
                and obj.db.spawn_room == room
            ]
        )

    def _spawn(self, proto: Any, room: Any) -> None:
        npc = None
        proto = self._normalize_proto(proto)
        proto_is_digit = isinstance(proto, int)
        room_ref = getattr(room, "dbref", room)
        room_id = getattr(room.db, "room_id", None)
        try:
            if proto_is_digit:
                from world.scripts.mob_db import get_mobdb

                mob_db = get_mobdb()
                if mob_db.get_proto(proto):
                    npc = spawn_from_vnum(int(proto), location=room)
                    npc.db.prototype_key = int(proto)
                else:
                    p_data = prototypes.get_npc_prototypes().get(str(proto))
                    if not p_data:
                        logger.log_warn(
                            f"SpawnManager: prototype {proto} not found for room {room_ref} (id {room_id}) after MobDB and JSON lookup"
                        )
                        return
                    logger.log_warn(
                        f"SpawnManager: NPC VNUM '{proto}' missing from MobDB; using JSON registry prototype for room {room_ref} (id {room_id})"
                    )
                    data = dict(p_data)
                    base_cls = data.get("typeclass", "typeclasses.npcs.BaseNPC")
                    if isinstance(base_cls, str):
                        module, clsname = base_cls.rsplit(".", 1)
                        base_cls = getattr(__import__(module, fromlist=[clsname]), clsname)
                    data["typeclass"] = f"{base_cls.__module__}.{base_cls.__name__}"
                    npc = spawner.spawn(data)[0]
                    npc.location = room
                    npc.db.prototype_key = proto
                    apply_proto_items(npc, data)
            else:
                p_data = prototypes.get_npc_prototypes().get(str(proto))
                if not p_data:
                    logger.log_warn(
                        f"SpawnManager: prototype {proto} not found for room {room_ref} (id {room_id}) in JSON registry"
                    )
                    return
                data = dict(p_data)
                base_cls = data.get("typeclass", "typeclasses.npcs.BaseNPC")
                if isinstance(base_cls, str):
                    module, clsname = base_cls.rsplit(".", 1)
                    base_cls = getattr(__import__(module, fromlist=[clsname]), clsname)
                data["typeclass"] = f"{base_cls.__module__}.{base_cls.__name__}"
                npc = spawner.spawn(data)[0]
                npc.location = room
                npc.db.prototype_key = proto
                apply_proto_items(npc, data)
        except Exception as err:
            logger.log_err(
                f"SpawnManager: failed to spawn {proto} in room {room_ref} (id {room_id}): {err}"
            )
            return

        if npc:
            npc.db.spawn_room = room
            npc.db.area_tag = room.db.area
            if not proto_is_digit:
                try:
                    from commands.npc_builder import finalize_mob_prototype
                    finalize_mob_prototype(npc, npc)
                except Exception as err:
                    logger.log_err(f"Finalize error on {npc}: {err}")
        return npc

    # ------------------------------------------------------------
    # script hooks
    # ------------------------------------------------------------
    def at_start(self):
        for entry in self.db.entries:
            room = self._get_room(entry)
            proto = entry.get("prototype")
            if not room:
                logger.log_warn(f"SpawnManager: room {entry.get('room')} not found for {proto}")
                continue
            existing = self._live_count(proto, room)
            max_count = entry.get("max_count", 1)
            if existing >= max_count:
                logger.log_info(f"SpawnManager: skipping spawn in room {room.dbref} for {proto}; capacity {existing}/{max_count}")
                continue
            to_spawn = max(0, max_count - existing)
            for _ in range(to_spawn):
                if self._live_count(proto, room) < max_count:
                    npc = self._spawn(proto, room)
                    if npc:
                        entry.setdefault("spawned", []).append(npc.id)
                    entry["last_spawn"] = time.time()
                    logger.log_info(f"SpawnManager: spawned {proto} in room {room.dbref}")

    def at_repeat(self):
        self.db.tick_count = (self.db.tick_count or 0) + 1
        now = time.time()
        batch_size = int(self.db.batch_size or 1)
        tick_mod = self.db.tick_count % batch_size

        for entry in self.db.entries:
            rid = entry.get("room_id")
            if rid is None:
                rid = self._normalize_room_id(entry.get("room"))
            hash_value = rid if rid is not None else hash(str(entry.get("room")))
            if batch_size > 1 and hash_value % batch_size != tick_mod:
                continue

            room = self._get_room(entry)
            proto = entry.get("prototype")
            if not room:
                logger.log_warn(f"SpawnManager: room {entry.get('room')} not found for {proto}")
                continue

            # clean out any expired death timers
            respawn = entry.get("respawn_rate", self.interval)
            ready = [ts for ts in entry.get("dead_timestamps", []) if now - ts >= respawn]
            entry["dead_timestamps"] = [ts for ts in entry.get("dead_timestamps", []) if now - ts < respawn]

            max_count = entry.get("max_count", 0)
            capacity = max(0, max_count - len(entry.get("spawned", [])))
            logger.log_debug(
                f"SpawnManager: processing room {self._normalize_room_id(entry)} for {proto} - {len(entry.get('spawned', []))}/{max_count}"
            )

            to_spawn = min(capacity, len(ready))
            for _ in range(to_spawn):
                npc = self._spawn(proto, room)
                if npc:
                    entry.setdefault("spawned", []).append(npc.id)
                if ready:
                    ready.pop(0)



