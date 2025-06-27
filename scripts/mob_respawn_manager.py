from __future__ import annotations

import time
from typing import Any, Dict, List

from evennia.objects.models import ObjectDB
from evennia.prototypes import spawner
from evennia.utils import logger, search

from typeclasses.rooms import Room
from typeclasses.scripts import Script
from utils.mob_proto import apply_proto_items, spawn_from_vnum
from world import prototypes


class MobRespawnTracker:
    """Track respawns for a single area."""

    def __init__(self, area: str):
        self.area = (area or "").lower()
        self.rooms: Dict[int, Room] = {}

    # ------------------------------------------------------------
    # public API
    # ------------------------------------------------------------
    def add_room(self, room: Room) -> None:
        rid = getattr(room.db, "room_id", None)
        if rid is not None:
            self.rooms[rid] = room

    def remove_room(self, room: Room) -> None:
        rid = getattr(room.db, "room_id", None)
        if rid is not None and rid in self.rooms:
            self.rooms.pop(rid)

    def record_death(
        self, prototype: Any, room: Room, npc_id: int | None = None
    ) -> None:
        norm = self._normalize_proto(prototype)
        entries = room.db.spawn_entries or []
        now = time.time()
        for idx, entry in enumerate(entries):
            if self._normalize_proto(entry.get("prototype")) != norm:
                continue
            active = [sid for sid in entry.get("active_mobs", []) if sid != npc_id]
            entry["active_mobs"] = active
            if npc_id is not None:
                dead = entry.get("dead_mobs", [])
                dead.append({"id": npc_id, "time_of_death": now})
                entry["dead_mobs"] = dead
            entry["last_spawn"] = now
            entries[idx] = entry
            break
        room.db.spawn_entries = entries
        room.save()

    def record_spawn(
        self, prototype: Any, room: Room, npc_id: int | None = None
    ) -> None:
        norm = self._normalize_proto(prototype)
        entries = room.db.spawn_entries or []
        for idx, entry in enumerate(entries):
            if self._normalize_proto(entry.get("prototype")) != norm:
                continue
            if npc_id is not None:
                active = entry.get("active_mobs", [])
                if npc_id not in active:
                    active.append(npc_id)
                    entry["active_mobs"] = active
            entry["last_spawn"] = time.time()
            entries[idx] = entry
            break
        room.db.spawn_entries = entries
        room.save()

    def process_room(self, room: Room) -> None:
        now = time.time()
        entries = room.db.spawn_entries or []
        updated = False
        for idx, entry in enumerate(entries):
            proto = entry.get("prototype")
            max_count = entry.get("max_count", 0)
            respawn = entry.get("respawn_rate", 60)
            live_objs = [
                obj
                for obj in room.contents
                if self._normalize_proto(getattr(obj.db, "prototype_key", None))
                == self._normalize_proto(proto)
                and obj.db.spawn_room == room
            ]
            live_count = len(live_objs)
            entry["active_mobs"] = [obj.id for obj in live_objs]
            dead_list = entry.get("dead_mobs", [])
            ready = [d for d in dead_list if now - d.get("time_of_death", 0) >= respawn]
            remaining = [
                d for d in dead_list if now - d.get("time_of_death", 0) < respawn
            ]
            if (
                not ready
                and live_count < max_count
                and now - entry.get("last_spawn", 0) >= respawn
            ):
                ready.append({})
            to_spawn = min(max_count - live_count, len(ready))
            for _ in range(to_spawn):
                npc = self._spawn(proto, room)
                if npc:
                    entry["active_mobs"].append(npc.id)
                    entry["last_spawn"] = now
                if ready:
                    ready.pop(0)
            entry["dead_mobs"] = remaining + ready
            entries[idx] = entry
            updated = True
        if updated:
            room.db.spawn_entries = entries
            room.save()

    def process(self) -> None:
        for room in list(self.rooms.values()):
            if not room.pk:
                self.remove_room(room)
                continue
            if not (room.db.spawn_entries):
                continue
            self.process_room(room)

    # ------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------
    def _normalize_proto(self, proto: Any) -> Any:
        if isinstance(proto, int):
            return proto
        try:
            if str(proto).isdigit():
                return int(proto)
        except Exception:
            pass
        return proto

    def _spawn(self, proto: Any, room: Room):
        npc = None
        proto = self._normalize_proto(proto)
        proto_is_digit = isinstance(proto, int)
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
                            f"RespawnManager: prototype {proto} not found for room {room.dbref}"
                        )
                        return None
                    logger.log_warn(
                        f"RespawnManager: NPC VNUM '{proto}' missing from MobDB; using registry"
                    )
                    data = dict(p_data)
                    base_cls = data.get("typeclass", "typeclasses.npcs.BaseNPC")
                    if isinstance(base_cls, str):
                        module, clsname = base_cls.rsplit(".", 1)
                        base_cls = getattr(
                            __import__(module, fromlist=[clsname]), clsname
                        )
                    data["typeclass"] = f"{base_cls.__module__}.{base_cls.__name__}"
                    npc = spawner.spawn(data)[0]
                    npc.location = room
                    npc.db.prototype_key = proto
                    apply_proto_items(npc, data)
            else:
                p_data = prototypes.get_npc_prototypes().get(str(proto))
                if not p_data:
                    logger.log_warn(
                        f"RespawnManager: prototype {proto} not found for room {room.dbref}"
                    )
                    return None
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
                f"RespawnManager: failed to spawn {proto} in room {room.dbref}: {err}"
            )
            return None

        if npc:
            npc.db.spawn_room = room
            npc.db.area_tag = room.db.area
            try:
                from commands.npc_builder import finalize_mob_prototype

                if not proto_is_digit:
                    finalize_mob_prototype(npc, npc)
            except Exception as err:
                logger.log_err(f"Finalize error on {npc}: {err}")
        return npc


class MobRespawnManager(Script):
    """Global script handling mob respawns for all areas."""

    def at_script_creation(self):
        if self.pk:
            self.key = "mob_respawn_manager"
            self.desc = "Handles mob respawning"
        else:
            self.db_key = "mob_respawn_manager"
            self.db_desc = "Handles mob respawning"
        self.interval = 60
        self.persistent = True
        self.repeats = -1
        self.start_delay = False
        self.db.trackers = self.db.trackers or {}

    # ------------------------------------------------------------
    # public API
    # ------------------------------------------------------------
    def get_tracker(self, area: str) -> MobRespawnTracker:
        area = (area or "").lower()
        trackers = self.db.trackers or {}
        tracker = trackers.get(area)
        if not tracker:
            tracker = MobRespawnTracker(area)
            trackers[area] = tracker
            self.db.trackers = trackers
        return tracker

    def register_room_spawn(self, proto: Dict[str, Any]) -> None:
        spawns = proto.get("spawns") or []
        room_id = proto.get("room_id") or proto.get("vnum")
        if room_id is None:
            return
        objs = ObjectDB.objects.get_by_attribute(key="room_id", value=int(room_id))
        room = objs[0] if objs else None
        if not room:
            return
        entries: List[Dict[str, Any]] = []
        for entry in spawns:
            proto_key = entry.get("prototype") or entry.get("proto")
            if not proto_key:
                continue
            entries.append(
                {
                    "area": (proto.get("area") or "").lower(),
                    "prototype": (
                        int(proto_key) if str(proto_key).isdigit() else proto_key
                    ),
                    "room_id": int(room_id),
                    "max_count": int(
                        entry.get("max_spawns", entry.get("max_count", 1))
                    ),
                    "respawn_rate": int(
                        entry.get("spawn_interval", entry.get("respawn_rate", 60))
                    ),
                    "active_mobs": [],
                    "dead_mobs": [],
                    "last_spawn": 0.0,
                }
            )
        room.db.spawn_entries = entries
        room.save()
        tracker = self.get_tracker(room.db.area)
        tracker.add_room(room)

    def force_respawn(self, room_vnum: int) -> None:
        objs = ObjectDB.objects.get_by_attribute(key="room_id", value=room_vnum)
        room = objs[0] if objs else None
        if not room:
            return
        tracker = self.get_tracker(room.db.area)
        tracker.add_room(room)
        tracker.process_room(room)

    def record_death(
        self, prototype: Any, room: Room, npc_id: int | None = None
    ) -> None:
        tracker = self.get_tracker(room.db.area)
        tracker.record_death(prototype, room, npc_id)

    def record_spawn(
        self, prototype: Any, room: Room, npc_id: int | None = None
    ) -> None:
        tracker = self.get_tracker(room.db.area)
        tracker.record_spawn(prototype, room, npc_id)

    # ------------------------------------------------------------
    # script hooks
    # ------------------------------------------------------------
    def at_repeat(self):
        trackers = self.db.trackers or {}
        from evennia.objects.models import ObjectDB

        objs = ObjectDB.objects.get_by_attribute(key="spawn_entries")
        area_map: Dict[str, List[Room]] = {}
        for room in objs:
            if not room.db.spawn_entries:
                continue
            area = (room.db.area or "").lower()
            area_map.setdefault(area, []).append(room)
        for area, rooms in area_map.items():
            tracker = self.get_tracker(area)
            tracker.rooms = {getattr(r.db, "room_id", 0): r for r in rooms}
            tracker.process()
        self.db.trackers = trackers
