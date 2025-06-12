from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Tuple

from django.conf import settings

__all__ = [
    "VNUM_RANGES",
    "validate_vnum",
    "register_vnum",
    "unregister_vnum",
    "get_next_vnum",
    "get_next_vnum_for_area",
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


def unregister_vnum(vnum: int, category: str) -> None:
    """Remove ``vnum`` from the registry for ``category``."""
    if category not in VNUM_RANGES:
        raise KeyError(f"Unknown category: {category}")
    data = _load()
    entry = data.get(category, {"used": [], "next": VNUM_RANGES[category][0]})
    used = set(entry.get("used", []))
    if vnum in used:
        used.remove(vnum)
        entry["used"] = sorted(used)
        if vnum < entry.get("next", VNUM_RANGES[category][0]):
            entry["next"] = vnum
        data[category] = entry
        _save(data)


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


def get_next_vnum_for_area(area_name: str, category: str, *, builder: str | None = None) -> int:
    """Return and reserve the next available VNUM for ``category`` in ``area_name``.

    The area's valid VNUM range is read from :mod:`world.areas`. If ``builder``
    is given, they must be listed as an authorized builder for the area. The
    returned VNUM will be persisted as used in the registry.
    """
    from world.areas import get_area_vnum_range, find_area

    if category not in VNUM_RANGES:
        raise KeyError(f"Unknown category: {category}")

    area_range = get_area_vnum_range(area_name)
    if not area_range:
        raise ValueError(f"Unknown area: {area_name}")
    if builder is not None:
        _, area = find_area(area_name)
        if area and area.builders and builder not in area.builders:
            raise PermissionError("Builder not authorized for this area")

    cat_start, cat_end = VNUM_RANGES[category]
    start = max(area_range[0], cat_start)
    end = min(area_range[1], cat_end)
    if start > end:
        raise ValueError("Area range does not overlap with category range")

    data = _load()
    entry = data.setdefault(category, {"used": [], "next": start})
    used = set(entry.get("used", []))

    # start searching from the larger of area start or stored next counter
    vnum = max(entry.get("next", start), start)
    for num in range(vnum, end + 1):
        if num not in used:
            vnum = num
            break
    else:
        for num in range(start, vnum):
            if num not in used:
                vnum = num
                break
        else:
            raise ValueError("No available VNUMs in area range")

    used.add(vnum)
    entry["used"] = sorted(used)
    entry["next"] = vnum + 1
    data[category] = entry
    _save(data)
    return vnum

