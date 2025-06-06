# State manager for temporary effects and cooldowns

from typing import Dict, List
from world import stats
from world.system import stat_manager
from world.effects import EFFECTS
from .constants import MAX_SATED, MAX_LEVEL


def _get_bonus_dict(chara) -> Dict[str, List[dict]]:
    return chara.db.temp_bonuses or {}


def _save_bonus_dict(chara, data):
    chara.db.temp_bonuses = data


def _get_status_dict(chara) -> Dict[str, int]:
    return chara.db.status_effects or {}


def _save_status_dict(chara, data):
    chara.db.status_effects = data


def _get_effect_dict(chara) -> Dict[str, int]:
    return chara.db.active_effects or {}


def _save_effect_dict(chara, data):
    chara.db.active_effects = data


def add_temp_stat_bonus(
    chara, stat: str, amount: int, duration: int, effect_key: str | None = None
):
    """Add a temporary bonus to ``stat`` lasting ``duration`` ticks.

    Args:
        chara: Character getting the bonus.
        stat: Stat to modify.
        amount: Bonus amount.
        duration: Number of ticks bonus lasts.
        effect_key: Optional identifier for the effect providing this bonus.
    """

    bonuses = _get_bonus_dict(chara)
    bonuses.setdefault(stat, []).append(
        {"amount": amount, "duration": duration, "key": effect_key}
    )
    _save_bonus_dict(chara, bonuses)
    stat_manager.refresh_stats(chara)


def remove_temp_stat_bonus(chara, stat: str, effect_key: str | None = None):
    """Remove temporary bonuses for ``stat``.

    If ``effect_key`` is provided, only bonuses matching that key are
    removed. Otherwise all bonuses for the stat are cleared.
    """

    bonuses = _get_bonus_dict(chara)
    if stat not in bonuses:
        return

    if effect_key is None:
        del bonuses[stat]
    else:
        bonuses[stat] = [
            entry for entry in bonuses[stat] if entry.get("key") != effect_key
        ]
        if not bonuses[stat]:
            del bonuses[stat]
    _save_bonus_dict(chara, bonuses)
    stat_manager.refresh_stats(chara)


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


def add_effect(chara, key: str, duration: int):
    """Add an active effect with a duration."""
    effects = _get_effect_dict(chara)
    effects[key] = duration
    _save_effect_dict(chara, effects)
    effect = EFFECTS.get(key)
    if effect and effect.type == "buff":
        chara.tags.add(key, category="buff")
    else:
        chara.tags.add(key, category="status")
    stat_manager.refresh_stats(chara)


def remove_effect(chara, key: str):
    """Remove an active effect from ``chara``."""
    effects = _get_effect_dict(chara)
    if key in effects:
        del effects[key]
        _save_effect_dict(chara, effects)
        chara.tags.remove(key, category="buff")
        chara.tags.remove(key, category="status")
        stat_manager.refresh_stats(chara)


def get_effect_mods(chara) -> Dict[str, int]:
    """Return aggregated stat modifiers from active effects."""
    mods: Dict[str, int] = {}
    for key in _get_effect_dict(chara):
        effect = EFFECTS.get(key)
        if not effect or not effect.mods:
            continue
        for stat, amt in effect.mods.items():
            mods[stat] = mods.get(stat, 0) + amt
    return mods


def get_temp_bonus(chara, stat: str) -> int:
    total = 0
    for entry in _get_bonus_dict(chara).get(stat, []):
        total += entry.get("amount", 0)
    return total


def get_effective_stat(chara, stat: str) -> int:
    """Return ``stat`` value including temporary bonuses."""
    base = stats.sum_bonus(chara, stat)
    base += get_temp_bonus(chara, stat)
    base += get_effect_mods(chara).get(stat, 0)
    return base


def tick_character(chara):
    """Advance effect timers on ``chara`` and expire as needed."""
    bonuses = _get_bonus_dict(chara)
    changed = False
    for stat, entries in list(bonuses.items()):
        for entry in list(entries):
            # duration counts down while preserving the effect key
            entry["duration"] -= 1
            if entry["duration"] <= 0:
                entries.remove(entry)
                changed = True
        if not entries:
            del bonuses[stat]
            changed = True
    if changed:
        _save_bonus_dict(chara, bonuses)
        stat_manager.refresh_stats(chara)

    effects = _get_effect_dict(chara)
    effect_changed = False
    for key, dur in list(effects.items()):
        dur -= 1
        if dur <= 0:
            del effects[key]
            chara.tags.remove(key, category="buff")
            chara.tags.remove(key, category="status")
            effect_changed = True
        else:
            effects[key] = dur
    if effect_changed:
        _save_effect_dict(chara, effects)
        stat_manager.refresh_stats(chara)

    statuses = _get_status_dict(chara)
    status_changed = False
    for status, dur in list(statuses.items()):
        dur -= 1
        if dur <= 0:
            del statuses[status]
            chara.tags.remove(status, category="status")
            status_changed = True
        else:
            statuses[status] = dur
    if status_changed:
        _save_status_dict(chara, statuses)
        stat_manager.refresh_stats(chara)

    # Hunger and thirst is ignored for max-level characters
    if hasattr(chara.db, "sated") and (chara.db.level or 1) < MAX_LEVEL:
        sated = min(chara.db.sated or 0, MAX_SATED)
        if sated > 0:
            chara.db.sated = sated - 1
        if chara.db.sated <= 0:
            chara.db.sated = 0
            add_effect(chara, "hungry_thirsty", 1)
            if (hp := chara.traits.get("health")):
                hp.current = max(hp.current - 1, 0)


def tick_all():
    """Tick timers for all characters."""
    from typeclasses.characters import Character

    for chara in Character.objects.all():
        tick_character(chara)
