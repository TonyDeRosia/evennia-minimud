"""Common utilities for the combat engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from world.system import state_manager

# For every ``HASTE_PER_EXTRA_ATTACK`` haste, an actor gains one additional
# attack in a round (up to ``MAX_ATTACKS_PER_ROUND`` total).
HASTE_PER_EXTRA_ATTACK = 50
MAX_ATTACKS_PER_ROUND = 6


@dataclass
class CombatParticipant:
    """Representation of a combatant in combat."""

    actor: object
    initiative: int = 0
    next_action: List[object] = field(default_factory=list)


def _current_hp(obj):
    """Return the current health of ``obj`` as an integer."""
    if hasattr(obj, "hp"):
        try:
            return int(obj.hp)
        except Exception:
            pass
    hp_trait = getattr(getattr(obj, "traits", None), "health", None)
    if hp_trait is not None:
        try:
            return int(hp_trait.value)
        except Exception:
            return 0
    return 0

