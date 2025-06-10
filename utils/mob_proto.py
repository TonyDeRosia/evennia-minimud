"""Helpers for storing and spawning mob prototypes by VNUM."""

from __future__ import annotations

from typing import Optional

from evennia.prototypes import spawner
from world.scripts.mob_db import get_mobdb


def register_prototype(data: dict, vnum: int | None = None) -> int:
    """Register ``data`` in the mob database under ``vnum``."""
    mob_db = get_mobdb()
    if vnum is None:
        vnum = mob_db.next_vnum()
    mob_db.add_proto(vnum, data)
    return vnum


def get_prototype(vnum: int) -> Optional[dict]:
    """Return the prototype stored for ``vnum`` or ``None``."""
    return get_mobdb().get_proto(vnum)


def spawn_from_vnum(vnum: int, location=None):
    """Spawn and return an NPC from ``vnum`` prototype."""
    mob_db = get_mobdb()
    proto = mob_db.get_proto(vnum)
    if not proto:
        return None
    proto = dict(proto)
    npc = spawner.spawn(proto)[0]
    if location:
        npc.location = location
    npc.db.vnum = vnum
    # track how often this prototype has spawned
    proto["spawn_count"] = int(proto.get("spawn_count", 0)) + 1
    mob_db.add_proto(vnum, proto)
    return npc
