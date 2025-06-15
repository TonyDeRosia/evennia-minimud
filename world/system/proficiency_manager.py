"""Helper utilities for tracking skill and spell proficiency."""

from __future__ import annotations

from typing import Any, Tuple

from . import state_manager

# Maximum proficiency attainable via practice and overall cap
PRACTICE_CAP = 75
USE_CAP = 100

__all__ = ["PRACTICE_CAP", "USE_CAP", "practice", "record_use", "scaling_bonus"]


def scaling_bonus(chara) -> int:
    """Return bonus proficiency gain based on INT/WIS/LUCK."""
    int_stat = state_manager.get_effective_stat(chara, "INT")
    wis_stat = state_manager.get_effective_stat(chara, "WIS")
    luck_stat = state_manager.get_effective_stat(chara, "LUCK")
    return int((int_stat + wis_stat + luck_stat) / 300)


def _get_prof(obj: Any) -> int:
    return int(getattr(obj, "proficiency", 0))


def _set_prof(obj: Any, value: int) -> None:
    setattr(obj, "proficiency", int(value))


def practice(chara, prof_obj: Any, sessions: int = 1) -> Tuple[int, int]:
    """Spend practice sessions to raise ``prof_obj`` proficiency.

    Args:
        chara: Character using practice sessions.
        prof_obj: Object with a ``proficiency`` attribute.
        sessions: Number of sessions to spend.

    Returns:
        tuple: ``(spent, new_proficiency)``
    """

    if prof_obj is None:
        return 0, 0

    prof = _get_prof(prof_obj)
    spent = 0
    while spent < sessions and chara.db.practice_sessions > 0 and prof < PRACTICE_CAP:
        prof = 25 if prof == 0 else min(PRACTICE_CAP, prof + 25)
        chara.db.practice_sessions -= 1
        spent += 1
    _set_prof(prof_obj, prof)
    return spent, prof


def record_use(chara, prof_obj: Any) -> int:
    """Record usage of ``prof_obj`` and apply guaranteed gains."""

    if not prof_obj:
        return 0

    key = getattr(prof_obj, "key", getattr(prof_obj, "name", None))
    if not key:
        return _get_prof(prof_obj)

    usage = chara.db.ability_usage or {}
    count = usage.get(key, 0) + 1
    usage[key] = count
    chara.db.ability_usage = usage

    prof = _get_prof(prof_obj)

    if count >= 25:
        if prof < USE_CAP:
            prof = min(USE_CAP, prof + 1)
            _set_prof(prof_obj, prof)
        usage[key] = 0
        chara.db.ability_usage = usage

    return prof
