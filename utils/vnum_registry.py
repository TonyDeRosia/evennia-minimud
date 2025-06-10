from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Tuple

from django.conf import settings

__all__ = [
    "VNUM_RANGES",
    "validate_vnum",
    "register_vnum",
    "get_next_vnum",
]

# Mapping of category -> (start, end) of allowed VNUM range
VNUM_RANGES: Dict[str, Tuple[int, int]] = {
    "npc": (1, 99999),
    "object": (100000, 199999),
    "room": (200000, 299999),
}

_REG_PATH = Path(getattr(settings, "VNUM_REGISTRY_FILE", Path(settings.GAME_DIR) / "world" / "vnum_registry.json"))


def _load() -> Dict[str, Dict]:
    try:
        with _REG_PATH.open("r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError:
        return {}


def _save(data: Dict[str, Dict]):
    _REG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _REG_PATH.open("w") as f:
        json.dump(data, f, indent=4)


def validate_vnum(vnum: int, category: str) -> bool:
    """Return ``True`` if ``vnum`` is valid and unused for ``category``."""
    if category not in VNUM_RANGES:
        raise KeyError(f"Unknown category: {category}")
    start, end = VNUM_RANGES[category]
    if not (start <= vnum <= end):
        return False
    data = _load()
    used = set(data.get(category, {}).get("used", []))
    return vnum not in used


def register_vnum(vnum: int):
    """Record ``vnum`` as used in its category."""
    data = _load()
    for cat, (start, end) in VNUM_RANGES.items():
        if start <= vnum <= end:
            entry = data.setdefault(cat, {"used": [], "next": start})
            if vnum not in entry["used"]:
                entry["used"].append(vnum)
                if entry["next"] <= vnum:
                    entry["next"] = vnum + 1
                data[cat] = entry
                _save(data)
            return
    raise ValueError("VNUM outside defined ranges")


def get_next_vnum(category: str) -> int:
    """Return and reserve the next available VNUM for ``category``."""
    if category not in VNUM_RANGES:
        raise KeyError(f"Unknown category: {category}")
    start, end = VNUM_RANGES[category]
    data = _load()
    entry = data.setdefault(category, {"used": [], "next": start})
    vnum = max(entry.get("next", start), start)
    used = set(entry.get("used", []))
    while vnum in used and vnum <= end:
        vnum += 1
    if vnum > end:
        raise ValueError("No available VNUMs in range")
    used.add(vnum)
    entry["used"] = sorted(used)
    entry["next"] = vnum + 1
    data[category] = entry
    _save(data)
    return vnum

