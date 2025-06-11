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
    "calculate_combat_stats",
    "mobprogs_to_triggers",
]


def assign_next_vnum(category: str) -> int:
    """Return and reserve the next available VNUM for ``category``."""
    return vnum_registry.get_next_vnum(category)


def add_to_mlist(vnum: int, prototype: Dict) -> None:
    """Insert ``prototype`` into the mob database under ``vnum``."""
    get_mobdb().add_proto(int(vnum), dict(prototype))


def calculate_combat_stats(combat_class: str, level: int) -> Dict[str, int]:
    """Return base combat stats for ``combat_class`` at ``level``."""
    base = int(level) * 10
    return {
        "hp": base,
        "mp": base // 2
        if combat_class.lower() in ("wizard", "sorcerer", "mage", "necromancer")
        else base // 4,
        "sp": base // 2
        if combat_class.lower() in ("warrior", "rogue", "swashbuckler")
        else base // 3,
        "armor": level * 2
        if combat_class.lower() in ("warrior", "paladin")
        else level,
        "initiative": 10 + level // 2,
    }


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
