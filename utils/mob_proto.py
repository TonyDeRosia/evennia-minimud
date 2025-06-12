"""Helpers for storing and spawning mob prototypes by VNUM."""

from __future__ import annotations

from typing import Optional

from evennia.prototypes import spawner
from world.scripts.mob_db import get_mobdb
from .vnum_registry import get_next_vnum, register_vnum, validate_vnum
from world import prototypes
from world.areas import get_area_vnum_range


def register_prototype(data: dict, vnum: int | None = None, *, area: str | None = None) -> int:
    """Register ``data`` in the mob database under ``vnum``.

    If ``area`` is given, ``vnum`` must fall within that area's range.
    """
    mob_db = get_mobdb()
    if vnum is None:
        vnum = get_next_vnum("npc")
        if area:
            rng = get_area_vnum_range(area)
            if rng and not (rng[0] <= vnum <= rng[1]):
                raise ValueError("VNUM outside area range")
    else:
        if area:
            rng = get_area_vnum_range(area)
            if rng and not (rng[0] <= vnum <= rng[1]):
                raise ValueError("VNUM outside area range")
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
    prototypes._normalize_proto(proto_data)
    if "typeclass" not in proto_data:
        proto_data["typeclass"] = "typeclasses.npcs.BaseNPC"

    # dynamically combine base class with role mixins
    base_cls = proto_data["typeclass"]
    if isinstance(base_cls, str):
        module, clsname = base_cls.rsplit(".", 1)
        base_cls = getattr(__import__(module, fromlist=[clsname]), clsname)

    metadata = proto_data.get("metadata") or {}
    role_names = metadata.get("roles") or []
    from commands.npc_builder import ROLE_MIXIN_MAP
    mixins = [ROLE_MIXIN_MAP[r] for r in role_names if r in ROLE_MIXIN_MAP]
    if mixins:
        dyn_class = type("DynamicNPC", tuple([base_cls, *mixins]), {})
        proto_data["typeclass"] = dyn_class
    else:
        proto_data["typeclass"] = base_cls

    npc = spawner.spawn(proto_data)[0]
    if location:
        npc.location = location
    npc.db.vnum = vnum
    npc.tags.add(f"M{vnum}", category="vnum")

    mobprogs = proto_data.get("mobprogs") or []
    npc.db.mobprogs = mobprogs

    from commands.npc_builder import finalize_mob_prototype
    finalize_mob_prototype(npc, npc)

    # track how often this prototype has spawned
    mob_db.increment_spawn_count(vnum)
    return npc
