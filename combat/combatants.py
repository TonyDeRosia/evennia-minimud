"""Utilities for working with combat participants."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, List


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
        except Exception as err:  # pragma: no cover - safety
            raise ValueError(f"invalid hp value on {obj!r}") from err

    hp_trait = getattr(getattr(obj, "traits", None), "health", None)
    if hp_trait is not None:
        try:
            return int(hp_trait.current)
        except Exception as err:  # pragma: no cover - safety
            raise ValueError(f"invalid health trait on {obj!r}") from err

    raise AttributeError(f"{obj!r} lacks a health trait or hp attribute")


# ---------------------------------------------------------------------------
# participant list helpers
# ---------------------------------------------------------------------------

def _assemble(*groups: Iterable[object] | object) -> List[object]:
    """Flatten one or more fighter groups into a participant list."""
    fighters: List[object] = []
    for grp in groups:
        if isinstance(grp, Iterable) and not isinstance(grp, (str, bytes)):
            fighters.extend(list(grp))
        else:
            fighters.append(grp)
    return fighters


def setup_1v1(a: object, b: object) -> List[object]:
    """Return a participant list for a one-on-one fight."""
    return _assemble(a, b)


def setup_1vN(a: object, opponents: Iterable[object]) -> List[object]:
    """Return a participant list for a one-versus-many fight."""
    return _assemble(a, opponents)


def setup_NvN(group_a: Iterable[object], group_b: Iterable[object]) -> List[object]:
    """Return a participant list for a group-vs-group fight."""
    return _assemble(group_a, group_b)
