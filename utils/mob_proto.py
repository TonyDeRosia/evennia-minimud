"""Helpers for storing and spawning mob prototypes by VNUM."""

from __future__ import annotations

from typing import Optional

from evennia.prototypes import spawner
from world.scripts.mob_db import get_mobdb
from .vnum_registry import get_next_vnum, register_vnum, validate_vnum
from .mob_utils import mobprogs_to_triggers


def register_prototype(data: dict, vnum: int | None = None) -> int:
    """Register ``data`` in the mob database under ``vnum``."""
    mob_db = get_mobdb()
    if vnum is None:
        vnum = get_next_vnum("npc")
    else:
        if not validate_vnum(vnum, "npc"):
            raise ValueError("Invalid or already used VNUM")
        register_vnum(vnum)
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
    proto_data = dict(proto)
    npc = spawner.spawn(proto_data)[0]
    if location:
        npc.location = location
    npc.db.vnum = vnum
    npc.tags.add(f"M{vnum}", category="vnum")

    mobprogs = proto_data.get("mobprogs") or []
    npc.db.mobprogs = mobprogs
    npc.db.triggers = mobprogs_to_triggers(mobprogs)

    from commands.npc_builder import finalize_mob_prototype
    finalize_mob_prototype(npc, npc)

    # track how often this prototype has spawned
    mob_db.increment_spawn_count(vnum)
    return npc
