from __future__ import annotations

"""Helpers for managing prototypes stored on disk.

This module centralizes handling of prototype files for different
categories (rooms, mobs, objects and areas). It also hooks into the
:mod:`utils.vnum_registry` to keep track of which VNUMs are in use and
to make sure VNUMs fall within defined ranges.
"""

from pathlib import Path
import json
from typing import Dict, Optional, Mapping, Sequence

from evennia.utils import logger

from django.conf import settings

from .vnum_registry import (
    VNUM_RANGES,
    get_next_vnum,
    register_vnum,
    validate_vnum,
)

__all__ = [
    "CATEGORY_DIRS",
    "load_prototype",
    "save_prototype",
    "load_all_prototypes",
    "is_in_range",
]

# Base ``prototypes`` directory under the game dir
_BASE_PATH = Path(settings.GAME_DIR) / "world" / "prototypes"

# Mapping of prototype category -> directory path
CATEGORY_DIRS: Dict[str, Path] = {
    "room": _BASE_PATH / "rooms",
    "npc": _BASE_PATH / "mobs",
    "object": _BASE_PATH / "objects",
    "area": _BASE_PATH / "areas",
}


def _json_safe(value):
    """Return ``value`` converted to JSON-serializable built-ins."""

    if isinstance(value, Mapping):
        return {k: _json_safe(v) for k, v in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_json_safe(v) for v in value]
    if isinstance(value, set):
        return [_json_safe(v) for v in value]
    return value


def _proto_file(category: str, vnum: int) -> Path:
    """Return absolute path for ``vnum`` in ``category``."""
    return CATEGORY_DIRS[category] / f"{int(vnum)}.json"


def load_prototype(category: str, vnum: int) -> Optional[dict]:
    """Load and return prototype ``vnum`` for ``category`` if it exists."""
    path = _proto_file(category, vnum)
    try:
        with path.open("r") as f:
            return json.load(f)
    except FileNotFoundError:
        return None
    except json.JSONDecodeError as err:
        # Propagate decode errors so callers can differentiate between an
        # unreadable file and one that simply does not exist.
        raise err


def load_all_prototypes(category: str) -> Dict[int, dict]:
    """Return mapping of all ``vnum`` -> prototype for ``category``."""
    result: Dict[int, dict] = {}
    directory = CATEGORY_DIRS[category]
    if not directory.exists():
        return result
    for file in directory.glob("*.json"):
        try:
            with file.open("r") as f:
                proto = json.load(f)
            try:
                result[int(file.stem)] = proto
            except ValueError:
                logger.log_info(f"Skipped non-numeric prototype file: {file.name}")
                continue
        except json.JSONDecodeError:
            continue
    return result


def save_prototype(category: str, data: dict, vnum: int | None = None) -> int:
    """Save ``data`` under ``vnum`` for ``category``.

    If ``vnum`` is ``None`` the next available number for the
    category will be used. The used ``vnum`` is returned.
    """
    if vnum is None:
        vnum = get_next_vnum(category)
    else:
        if validate_vnum(vnum, category):
            register_vnum(vnum)
    path = _proto_file(category, vnum)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        json.dump(_json_safe(data), f, indent=4)
    return vnum


def is_in_range(category: str, vnum: int) -> bool:
    """Return ``True`` if ``vnum`` falls within the allowed range."""
    if category not in VNUM_RANGES:
        raise KeyError(f"Unknown category: {category}")
    start, end = VNUM_RANGES[category]
    return start <= int(vnum) <= end
