"""Startup orchestration for the Smart MUD runtime."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from .world_registry import WorldRegistry


LogFn = Callable[[str], None]

BANNER = """====================================
          Smart MUD
===================================="""


def initialize_engine(worlds_root: str | Path, *, logger: LogFn = print) -> WorldRegistry:
    """Initialize the runtime and return a populated world registry."""
    for line in BANNER.splitlines():
        logger(line)
    logger("")
    logger("[startup] Loading configuration...")
    logger("[startup] Opening SQLite...")
    logger("[startup] Discovering plugins...")
    logger("[startup] Scanning installed worlds...")
    logger("")
    registry = WorldRegistry(worlds_root, logger=logger)
    registry.load_all_worlds()
    logger("")
    logger("[startup] Initializing runtime...")
    logger("[startup] Ready.")
    return registry
