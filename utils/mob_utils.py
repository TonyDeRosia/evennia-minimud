from __future__ import annotations

"""Helper utilities for NPC management and stat calculations."""

from typing import Dict

from utils import vnum_registry
from utils.stats_utils import normalize_stat_key
from world.scripts.mob_db import get_mobdb
from world.system import stat_manager

__all__ = [
    "auto_calc",
    "auto_calc_secondary",
    "assign_next_vnum",
    "add_to_mlist",
    "generate_base_stats",
    "calculate_combat_stats",
    "mobprogs_to_triggers",
    "make_corpse",
]


def assign_next_vnum(category: str) -> int:
    """Return and reserve the next available VNUM for ``category``."""
    return vnum_registry.get_next_vnum(category)


def add_to_mlist(vnum: int, prototype: Dict) -> None:
    """Insert ``prototype`` into the mob database under ``vnum``."""
    get_mobdb().add_proto(int(vnum), dict(prototype))


def generate_base_stats(class_name: str, level: int) -> Dict[str, int]:
    """Return default combat stats for ``class_name`` at ``level``."""

    base = int(level) * 10
    lower = class_name.lower()
    return {
        "hp": base,
        "mp": base // 2 if lower in ("wizard", "sorcerer", "mage", "necromancer") else base // 4,
        "sp": base // 2 if lower in ("warrior", "rogue", "swashbuckler") else base // 3,
        "armor": level * 2 if lower in ("warrior", "paladin") else level,
        "initiative": 10 + level // 2,
    }


def calculate_combat_stats(combat_class: str, level: int) -> Dict[str, int]:
    """Return base combat stats for ``combat_class`` at ``level``."""
    return generate_base_stats(combat_class, level)


def auto_calc(primary_stats: Dict[str, int]) -> Dict[str, int]:
    """Calculate derived stats from ``primary_stats`` using weight mappings."""
    prim = {normalize_stat_key(k): int(v) for k, v in primary_stats.items()}
    result: Dict[str, int] = {}
    for stat, mapping in stat_manager.STAT_SCALING.items():
        value = 0.0
        for key, weight in mapping.items():
            value += prim.get(key, 0) * weight
        result[stat] = int(round(value))
    return result


def auto_calc_secondary(primary_stats: Dict[str, int]) -> Dict[str, int]:
    """Return only non-resource stats from :func:`auto_calc`."""
    derived = auto_calc(primary_stats)
    for key in ("HP", "MP", "SP"):
        derived.pop(key, None)
    return derived


def mobprogs_to_triggers(mobprogs: list[dict]) -> Dict[str, list[dict]]:
    """Convert mobprogs to trigger format used by :class:`TriggerManager`."""

    result: Dict[str, list[dict]] = {}
    for prog in mobprogs or []:
        event = prog.get("type")
        if not event:
            continue
        entry = dict(prog.get("conditions") or {})
        entry["responses"] = prog.get("commands") or []
        result.setdefault(event, []).append(entry)
    return result


def make_corpse(npc):
    """Create a corpse object for ``npc`` and transfer belongings."""

    from evennia.utils import create
    from world.mob_constants import ACTFLAGS

    if not npc or not npc.location:
        return None

    # avoid multiple corpses if on_death is called repeatedly
    existing = [
        obj
        for obj in npc.location.contents
        if obj.is_typeclass("typeclasses.objects.Corpse", exact=False)
        and obj.db.corpse_of == npc.key
    ]
    if existing:
        return existing[0]

    attrs = [("corpse_of", npc.key)]
    if decay := getattr(npc.db, "corpse_decay_time", None):
        attrs.append(("decay_time", decay))
    corpse = create.create_object(
        "typeclasses.objects.Corpse",
        key=f"{npc.key} corpse",
        location=npc.location,
        attributes=attrs,
    )

    # move carried items
    for obj in list(npc.contents):
        obj.location = corpse

    moved = set()
    for item in npc.equipment.values():
        if item and item not in moved:
            item.location = corpse
            moved.add(item)

    # drop carried coins unless flagged NOLOOT
    if ACTFLAGS.NOLOOT.value not in (npc.db.actflags or []):
        for coin, amt in (npc.db.coins or {}).items():
            if int(amt):
                pile = create.create_object(
                    "typeclasses.objects.CoinPile",
                    key=f"{coin} coins",
                    location=corpse,
                )
                pile.db.coin_type = coin
                pile.db.amount = int(amt)

    return corpse

