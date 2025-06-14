# State manager for temporary effects and cooldowns

from typing import Dict, List
from world import stats
from world.system import stat_manager
from world.effects import EFFECTS
from django.conf import settings
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
    reduction = get_effective_stat(chara, "cooldown_reduction")
    if reduction:
        duration = max(0, int(round(duration * (1 - reduction / 100))))
    chara.cooldowns.add(key, duration)


def remove_cooldown(chara, key: str):
    """Remove a cooldown if it exists."""
    handler = getattr(chara, "cooldowns", None)
    if not handler:
        return
    if hasattr(handler, "remove"):
        handler.remove(key)
    else:
        try:
            del handler[key]
        except Exception:
            pass


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
    if not hasattr(chara, "traits"):
        return 0

    base = stats.sum_bonus(chara, stat)
    base += get_temp_bonus(chara, stat)
    base += get_effect_mods(chara).get(stat, 0)
    return base


def apply_regen(chara):
    """Apply resource regeneration to ``chara``.

    Adds ``health_regen``, ``mana_regen`` and ``stamina_regen`` values to the
    current amounts of their respective resources. The resulting values are
    capped at each resource's maximum.

    Args:
        chara: The character gaining regeneration.

    Returns:
        dict: Mapping of resource keys to the amount actually regenerated.
    """

    healed: Dict[str, int] = {}

    if not hasattr(chara, "traits"):
        return healed

    derived = getattr(chara.db, "derived_stats", {}) or {}

    statuses = chara.tags.get(category="status", return_list=True) or []
    if "sleeping" in statuses or "unconscious" in statuses:
        multiplier = 3
    elif any(s in statuses for s in ("sitting", "lying down")):
        multiplier = 2
    else:
        multiplier = 1

    location = getattr(chara, "location", None)
    if location and location.tags.has("rest_area", category="room_flag"):
        multiplier += 10

    for key in ("health", "mana", "stamina"):
        trait = chara.traits.get(key)
        if not trait:
            continue
        regen = int(derived.get(f"{key}_regen", 0))
        if regen <= 0 or trait.current >= trait.max:
            continue
        healed_amt = max(1, int(round(regen * multiplier)))
        new_val = min(trait.current + healed_amt, trait.max)
        gained = new_val - trait.current
        if gained:
            trait.current = new_val
            healed[key] = gained

    return healed


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
            drain_pct = 5  # percent of each resource to lose
            for key in ("health", "mana", "stamina"):
                if not (trait := chara.traits.get(key)):
                    continue
                max_val = trait.max or trait.current
                loss = max(1, int(round(max_val * drain_pct / 100)))
                trait.current = max(trait.current - loss, 0)


def tick_all():
    """Tick timers for all characters."""
    from typeclasses.characters import Character

    for chara in Character.objects.all():
        tick_character(chara)


def check_level_up(chara) -> bool:
    """Increase character level based on experience.

    Grants +3 practice sessions and +1 training point per level gained and
    notifies the character when a level up occurs.

    Args:
        chara: The character to check for leveling.

    Returns:
        bool: True if the character gained at least one level.
    """

    exp = int(chara.db.exp or 0)
    level = int(chara.db.level or 1)
    leveled = False

    while level < MAX_LEVEL and exp >= level * settings.XP_PER_LEVEL:
        level += 1
        leveled = True
        chara.db.practice_sessions = (chara.db.practice_sessions or 0) + 3
        chara.db.training_points = (chara.db.training_points or 0) + 1

    if leveled:
        chara.db.level = level
        chara.msg(f"You have reached level {level}!")
        chara.msg("You gain 3 practice sessions and 1 training session.")
        stat_manager.refresh_stats(chara)

    return leveled


def level_up(chara, excess: int = 0) -> None:
    """Increase ``chara.db.level`` and award practice/training."""

    level = int(chara.db.level or 1)
    if level >= MAX_LEVEL:
        return
    level += 1
    chara.db.level = level
    chara.db.practice_sessions = (chara.db.practice_sessions or 0) + 3
    chara.db.training_points = (chara.db.training_points or 0) + 1
    chara.db.tnl = settings.XP_PER_LEVEL
    if not settings.XP_CARRY_OVER:
        chara.db.experience = (chara.db.experience or 0) - excess
    chara.msg(f"You have reached level {level}!")
    chara.msg("You gain 3 practice sessions and 1 training session.")
    stat_manager.refresh_stats(chara)


def gain_xp(chara, amount: int) -> None:
    """Increase ``chara.db.experience`` and check for leveling."""

    if not chara or not amount:
        return

    amt = int(amount)
    chara.db.experience = (chara.db.experience or 0) + amt
    chara.db.tnl = (chara.db.tnl or settings.XP_PER_LEVEL) - amt

    while chara.db.tnl <= 0 and (chara.db.level or 1) < MAX_LEVEL:
        excess = -chara.db.tnl
        level_up(chara, excess)
        if settings.XP_CARRY_OVER:
            chara.db.tnl -= excess
        else:
            chara.db.tnl = settings.XP_PER_LEVEL

