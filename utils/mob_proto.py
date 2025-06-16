"""Helpers for storing and spawning mob prototypes by VNUM."""

from __future__ import annotations

from typing import Optional, Any

from evennia.prototypes import spawner
from evennia.utils import logger
from world.scripts.mob_db import get_mobdb
from .vnum_registry import get_next_vnum, register_vnum, validate_vnum
from world import prototypes
from world.areas import get_area_vnum_range


def register_prototype(
    data: dict, vnum: int | None = None, *, area: str | None = None
) -> int:
    """Register ``data`` in the mob database under ``vnum``.

    If ``area`` is given, ``vnum`` must fall within that area's range.
    """
    mob_db = get_mobdb()
    if "typeclass" in data:
        from typeclasses.characters import NPC

        tc = data["typeclass"]
        if isinstance(tc, type):
            if not issubclass(tc, NPC):
                raise ValueError(f"Typeclass {tc} does not inherit from NPC")
            data["typeclass"] = f"{tc.__module__}.{tc.__name__}"
        elif isinstance(tc, str):
            module, clsname = tc.rsplit(".", 1)
            try:
                cls = getattr(__import__(module, fromlist=[clsname]), clsname)
            except Exception as err:
                raise ValueError(f"Could not import typeclass '{tc}'") from err
            if not issubclass(cls, NPC):
                raise ValueError(f"Typeclass {tc} does not inherit from NPC")
        else:
            raise ValueError("typeclass must be a dotted path string or class object")

    # convert legacy skill/spell lists to dicts
    if isinstance(data.get("skills"), list):
        data["skills"] = {name: 100 for name in data["skills"]}
    if isinstance(data.get("spells"), list):
        data["spells"] = {name: 100 for name in data["spells"]}
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
        if validate_vnum(vnum, "npc"):
            register_vnum(vnum)
    mob_db.add_proto(vnum, data)

    key = data.get("key")
    if key:
        try:
            prototypes.register_npc_prototype(key, dict(data))
        except Exception:
            logger.log_err(f"Failed to register NPC prototype '{key}'")

    return vnum


def get_prototype(vnum: int) -> Optional[dict]:
    """Return the prototype stored for ``vnum`` or ``None``."""
    return get_mobdb().get_proto(vnum)


def _spawn_item(vnum: int) -> Any | None:
    """Spawn and return an item object from an object VNUM."""
    from .prototype_manager import load_prototype

    proto = load_prototype("object", int(vnum))
    if not proto:
        logger.log_err(f"Object prototype not found for VNUM {vnum}")
        return None
    return spawner.spawn(proto)[0]


def apply_proto_items(npc, proto_data: dict) -> None:
    """Spawn loot and equipment defined in ``proto_data`` onto ``npc``."""
    from utils.slots import normalize_slot

    loot_table = proto_data.get("loot_table") or []
    for entry in loot_table:
        proto = entry
        if isinstance(entry, dict):
            proto = entry.get("proto")
        if isinstance(proto, (int, str)) and str(proto).isdigit():
            item = _spawn_item(int(proto))
            if item:
                item.location = npc

    equipped = proto_data.get("equipped") or {}
    for slot, val in equipped.items():
        if not (isinstance(val, (int, str)) and str(val).isdigit()):
            continue
        item = _spawn_item(int(val))
        if not item:
            continue
        item.location = npc
        slot_norm = normalize_slot(slot) or slot
        try:
            if slot_norm in {"mainhand", "offhand", "twohanded", "mainhand/offhand", "left", "right"}:
                hand = None
                if slot_norm in {"mainhand", "right"}:
                    hand = "right"
                elif slot_norm in {"offhand", "left"}:
                    hand = "left"
                npc.at_wield(item, hand=hand)
            else:
                item.wear(npc, True)
        except Exception:
            pass


def spawn_from_vnum(vnum: int, location=None):
    """Spawn and return an NPC from ``vnum`` prototype."""
    mob_db = get_mobdb()
    proto = mob_db.get_proto(vnum)
    if not proto:
        raise ValueError(f"Prototype not found for VNUM {vnum}")
    from commands.npc_builder import validate_prototype  # lazy import

    warnings = validate_prototype(proto)
    if warnings:
        logger.log_warn(f"Prototype {vnum}: {'; '.join(warnings)}")
    missing = [field for field in ("key",) if not proto.get(field)]
    if missing:
        err = f"Prototype {vnum} missing required field(s): {', '.join(missing)}"
        logger.log_err(err)
        raise ValueError(err)
    proto_data = dict(proto)
    prototypes._normalize_proto(proto_data)
    if isinstance(proto_data.get("skills"), list):
        proto_data["skills"] = {name: 100 for name in proto_data["skills"]}
    if isinstance(proto_data.get("spells"), list):
        proto_data["spells"] = {name: 100 for name in proto_data["spells"]}
    if "typeclass" not in proto_data:
        proto_data["typeclass"] = "typeclasses.npcs.BaseNPC"

    # dynamically combine base class with role mixins
    base_cls = proto_data["typeclass"]
    if isinstance(base_cls, str):
        module, clsname = base_cls.rsplit(".", 1)
        base_cls = getattr(__import__(module, fromlist=[clsname]), clsname)

    from typeclasses.characters import NPC
    from typeclasses.npcs import BaseNPC

    if not issubclass(base_cls, NPC):
        logger.log_warn(
            f"Prototype {vnum}: {base_cls} is not a subclass of NPC; using BaseNPC."
        )
        base_cls = BaseNPC

    metadata = proto_data.get("metadata") or {}
    role_names = metadata.get("roles") or []
    from commands.npc_builder import ROLE_MIXIN_MAP

    mixins = [ROLE_MIXIN_MAP[r] for r in role_names if r in ROLE_MIXIN_MAP]
    dyn_class = None
    if mixins:
        dyn_class = type("DynamicNPC", tuple([base_cls, *mixins]), {})
    proto_data["typeclass"] = f"{base_cls.__module__}.{base_cls.__name__}"

    npc = spawner.spawn(proto_data)[0]
    if dyn_class:
        try:
            npc.swap_typeclass(dyn_class, clean_attributes=False)
        except Exception:  # fallback if swap_typeclass doesn't accept class
            npc.__class__ = dyn_class
    if location:
        npc.location = location
    npc.db.vnum = vnum
    npc.tags.add(f"M{vnum}", category="vnum")

    mobprogs = proto_data.get("mobprogs") or []
    npc.db.mobprogs = mobprogs

    apply_proto_items(npc, proto_data)

    from commands.npc_builder import finalize_mob_prototype

    finalize_mob_prototype(npc, npc)

    # track how often this prototype has spawned
    mob_db.increment_spawn_count(vnum)
    return npc
