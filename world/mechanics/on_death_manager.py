"""Centralized death handling helpers."""

from __future__ import annotations

from world.mechanics.death_handlers import get_handler, IDeathHandler
from combat.corpse_creation import spawn_corpse


def handle_death(victim, killer=None, handler: IDeathHandler | None = None):
    """Delegate death cleanup to the configured handler."""
    if handler is None:
        handler = get_handler()
    return handler.handle(victim, killer)
