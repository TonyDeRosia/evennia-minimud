"""Utility helpers for combat."""

import logging
import random
from typing import Tuple

from world.system import state_manager

logger = logging.getLogger(__name__)


def roll_damage(dice: Tuple[int, int]) -> int:
    """Roll NdN style damage."""
    count, sides = dice
    return sum(random.randint(1, sides) for _ in range(count))


def check_hit(attacker, target, bonus: int = 0) -> bool:
    """Determine if attacker hits target."""
    attack = state_manager.get_effective_stat(attacker, "accuracy") + bonus
    defense = state_manager.get_effective_stat(target, "dodge")
    roll = random.randint(1, 20)
    result = roll + attack >= 10 + defense
    logger.debug(
        "hit roll=%s att=%s def=%s result=%s",
        roll,
        attack,
        defense,
        result,
    )
    return result


def roll_crit(attacker, target) -> bool:
    """Return ``True`` if ``attacker`` scores a critical hit."""

    chance = state_manager.get_effective_stat(attacker, "crit_chance")
    chance -= state_manager.get_effective_stat(target, "crit_resist")
    chance = max(0, chance)
    roll = random.randint(1, 100)
    result = roll <= chance
    logger.debug(
        "crit roll=%s chance=%s result=%s",
        roll,
        chance,
        result,
    )
    return result


def crit_damage(attacker, damage: int) -> int:
    """Return ``damage`` adjusted by ``attacker``'s crit bonus."""

    bonus = state_manager.get_effective_stat(attacker, "crit_bonus")
    result = int(round(damage * (1 + bonus / 100)))
    logger.debug("crit damage=%s bonus=%s result=%s", damage, bonus, result)
    return result


def roll_evade(attacker, target, base: int = 50) -> bool:
    """Return ``True`` if ``target`` evades an attack from ``attacker``."""

    evade = state_manager.get_effective_stat(target, "evasion")
    acc = state_manager.get_effective_stat(attacker, "accuracy")
    chance = max(5, min(95, base + evade - acc))
    roll = random.randint(1, 100)
    result = roll <= chance
    logger.debug(
        "evade roll=%s chance=%s result=%s",
        roll,
        chance,
        result,
    )
    return result


def get_distance(a, b) -> int:
    """Return the Manhattan distance between ``a`` and ``b`` if possible."""

    loc_a = getattr(a, "location", a)
    loc_b = getattr(b, "location", b)
    if loc_a is loc_b:
        return 0
    if hasattr(loc_a, "xyz") and hasattr(loc_b, "xyz"):
        x1, y1, z1 = loc_a.xyz
        x2, y2, z2 = loc_b.xyz
        return abs(x1 - x2) + abs(y1 - y2) + abs(z1 - z2)
    return 9999


def check_distance(a, b, max_range: int) -> bool:
    """Return ``True`` if ``b`` is within ``max_range`` of ``a``."""

    dist = get_distance(a, b)
    result = dist <= max_range
    logger.debug("distance %s max=%s result=%s", dist, max_range, result)
    return result


def format_combat_message(
    actor,
    target,
    action: str,
    damage: int | None = None,
    *,
    crit: bool = False,
    miss: bool = False,
) -> str:
    """Return a standardized combat log message."""

    a_name = getattr(actor, "key", str(actor))
    t_name = getattr(target, "key", str(target))
    if miss:
        return f"{a_name}'s {action} misses {t_name}!"
    parts = [f"{a_name} {action} {t_name}"]
    if damage is not None:
        parts.append(f"for {damage} damage")
    if crit:
        parts.append("(critical)")
    return " ".join(parts) + "!"
