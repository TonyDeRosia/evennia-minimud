"""Utility helpers for combat."""

import logging
import random
from typing import Tuple

from world.system import state_manager
from world.system.stat_manager import check_hit, roll_crit, crit_damage

logger = logging.getLogger(__name__)


def roll_damage(dice: Tuple[int, int]) -> int:
    """Roll NdN style damage."""
    count, sides = dice
    return sum(random.randint(1, sides) for _ in range(count))


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


def roll_block(attacker, target, base: int = 0) -> bool:
    """Return ``True`` if ``target`` blocks an attack from ``attacker``."""

    block = state_manager.get_effective_stat(target, "block_rate")
    acc = state_manager.get_effective_stat(attacker, "accuracy")
    chance = max(0, min(95, base + block - acc))
    roll = random.randint(1, 100)
    result = roll <= chance
    logger.debug("block roll=%s chance=%s result=%s", roll, chance, result)
    return result


def roll_parry(attacker, target, base: int = 0) -> bool:
    """Return ``True`` if ``target`` parries an attack from ``attacker``."""

    parry = state_manager.get_effective_stat(target, "parry_rate")
    acc = state_manager.get_effective_stat(attacker, "accuracy")
    chance = max(0, min(95, base + parry - acc))
    roll = random.randint(1, 100)
    result = roll <= chance
    logger.debug("parry roll=%s chance=%s result=%s", roll, chance, result)
    return result


def apply_attack_power(attacker, damage: int) -> int:
    """Scale ``damage`` using ``attacker``'s attack power."""

    ap = state_manager.get_effective_stat(attacker, "attack_power")
    result = int(round(damage * (1 + ap / 100)))
    logger.debug("atk power=%s dmg=%s result=%s", ap, damage, result)
    return result


def apply_spell_power(caster, damage: int) -> int:
    """Scale ``damage`` using ``caster``'s spell power."""

    sp = state_manager.get_effective_stat(caster, "spell_power")
    result = int(round(damage * (1 + sp / 100)))
    logger.debug("spell power=%s dmg=%s result=%s", sp, damage, result)
    return result


def apply_lifesteal(attacker, damage: int) -> None:
    """Heal attacker based on damage dealt."""

    if not damage:
        return
    hp = getattr(attacker.traits, "health", None)
    mp = getattr(attacker.traits, "mana", None)
    ls = state_manager.get_effective_stat(attacker, "lifesteal")
    leech = state_manager.get_effective_stat(attacker, "leech")
    if hp and ls:
        heal = int(damage * ls / 100)
        hp.current = min(hp.current + heal, hp.max)
    if mp and leech:
        gain = int(damage * leech / 100)
        mp.current = min(mp.current + gain, mp.max)


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


def get_condition_msg(hp: int, max_hp: int) -> str:
    """Return a short description of current health."""

    percent = hp * 100 // max_hp if max_hp else 0
    if percent >= 100:
        return "is in excellent condition."
    if percent >= 75:
        return "is slightly wounded."
    if percent >= 50:
        return "is wounded."
    if percent >= 25:
        return "is covered in blood."
    if percent >= 10:
        return "is badly injured."
    if percent > 0:
        return "is mortally wounded."
    return "is dead."
