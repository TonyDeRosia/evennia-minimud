# State manager for temporary effects and cooldowns

from typing import Dict, List
from world import stats


def _get_bonus_dict(chara) -> Dict[str, List[dict]]:
    return chara.db.temp_bonuses or {}


def _save_bonus_dict(chara, data):
    chara.db.temp_bonuses = data


def _get_status_dict(chara) -> Dict[str, int]:
    return chara.db.status_effects or {}


def _save_status_dict(chara, data):
    chara.db.status_effects = data


def add_temp_stat_bonus(chara, stat: str, amount: int, duration: int):
    """Add a temporary bonus to ``stat`` lasting ``duration`` ticks."""
    bonuses = _get_bonus_dict(chara)
    bonuses.setdefault(stat, []).append({"amount": amount, "duration": duration})
    _save_bonus_dict(chara, bonuses)


def remove_temp_stat_bonus(chara, stat: str):
    """Remove all temporary bonuses for ``stat``."""
    bonuses = _get_bonus_dict(chara)
    if stat in bonuses:
        del bonuses[stat]
        _save_bonus_dict(chara, bonuses)


def add_status_effect(chara, status: str, duration: int):
    """Add a status effect tag lasting ``duration`` ticks."""
    statuses = _get_status_dict(chara)
    statuses[status] = duration
    chara.tags.add(status, category="status")
    _save_status_dict(chara, statuses)


def remove_status_effect(chara, status: str):
    """Remove ``status`` from ``chara``."""
    statuses = _get_status_dict(chara)
    if status in statuses:
        del statuses[status]
        chara.tags.remove(status, category="status")
        _save_status_dict(chara, statuses)


def has_status(chara, status: str) -> bool:
    """Return True if ``chara`` currently has ``status`` active."""
    statuses = _get_status_dict(chara)
    return status in statuses


def add_cooldown(chara, key: str, duration: int):
    """Wrapper to add a cooldown to ``chara``."""
    chara.cooldowns.add(key, duration)


def remove_cooldown(chara, key: str):
    """Remove a cooldown."""
    chara.cooldowns.remove(key)


def get_temp_bonus(chara, stat: str) -> int:
    total = 0
    for entry in _get_bonus_dict(chara).get(stat, []):
        total += entry.get("amount", 0)
    return total


def get_effective_stat(chara, stat: str) -> int:
    """Return ``stat`` value including temporary bonuses."""
    base = stats.sum_bonus(chara, stat)
    return base + get_temp_bonus(chara, stat)


def tick_character(chara):
    """Advance effect timers on ``chara`` and expire as needed."""
    bonuses = _get_bonus_dict(chara)
    changed = False
    for stat, entries in list(bonuses.items()):
        for entry in list(entries):
            entry["duration"] -= 1
            if entry["duration"] <= 0:
                entries.remove(entry)
                changed = True
        if not entries:
            del bonuses[stat]
            changed = True
    if changed:
        _save_bonus_dict(chara, bonuses)

    statuses = _get_status_dict(chara)
    for status, dur in list(statuses.items()):
        dur -= 1
        if dur <= 0:
            del statuses[status]
            chara.tags.remove(status, category="status")
        else:
            statuses[status] = dur
    _save_status_dict(chara, statuses)


def tick_all():
    """Tick timers for all characters."""
    from typeclasses.characters import Character

    for chara in Character.objects.all():
        tick_character(chara)
