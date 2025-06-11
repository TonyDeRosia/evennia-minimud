from __future__ import annotations

"""Utilities for registering mobs to the global mob list."""

from typing import Any, Dict
from utils.mob_utils import add_to_mlist


def register_mob_vnum(vnum: int, prototype: Any) -> None:
    """Record ``prototype`` in the mob database under ``vnum``."""
    if hasattr(prototype, "db"):
        data: Dict[str, Any] = {
            "key": getattr(prototype, "key", ""),
            "level": getattr(prototype.db, "level", None),
            "class": getattr(prototype.db, "charclass", None),
            "proto_key": getattr(prototype.db, "prototype_key", None),
        }
    else:
        data = dict(prototype)
    add_to_mlist(int(vnum), data)
