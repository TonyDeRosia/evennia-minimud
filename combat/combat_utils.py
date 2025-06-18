"""Utility helpers for combat."""

import logging
import random
import re
from typing import Tuple, Iterable

from world.system import state_manager
from world.system.stat_manager import check_hit, roll_crit, crit_damage


def award_xp(killer, total_xp: int, participants: Iterable | None = None) -> None:
    """Distribute ``total_xp`` among ``participants``.

    Parameters
    ----------
    killer
        Character credited with the kill.
    total_xp
        Amount of experience to award.
    participants
        Iterable of characters who contributed to the kill. ``killer`` will be
        included if not already present.
    """

    members = list(participants or [])
    if killer and killer not in members:
        members.insert(0, killer)

    members = [m for m in members if m]
    if not members or not total_xp:
        return

    share = max(int(total_xp / len(members)), int(total_xp * 0.10))
    for member in members:
        if hasattr(member, "msg"):
            member.msg(f"You gain |Y{share}|n experience points!")
        state_manager.gain_xp(member, share)


def calculate_initiative(combatant) -> int:
    """Return an initiative roll using DEX, level and gear bonuses."""

    base = 0
    if hasattr(combatant, "traits"):
        trait = combatant.traits.get("initiative")
        if trait:
            base = trait.value
    else:
        base = getattr(combatant, "initiative", 0)

    level = getattr(getattr(combatant, "db", None), "level", 1) or 1
    level_bonus = level // 4

    equip_bonus = 0
    equipment = getattr(combatant, "equipment", None)
    if isinstance(equipment, dict):
        for item in equipment.values():
            if not item:
                continue
            if hasattr(item, "attributes"):
                equip_bonus += item.attributes.get("initiative_bonus", default=0)
            else:
                getter = getattr(getattr(item, "db", None), "get", None)
                if callable(getter):
                    try:
                        equip_bonus += getter("initiative_bonus", 0)
                    except Exception:
                        pass

    return base + level_bonus + equip_bonus + random.randint(1, 20)

logger = logging.getLogger(__name__)


def roll_damage(dice: Tuple[int, int]) -> int:
    """Roll NdN style damage."""
    count, sides = dice
    return sum(random.randint(1, sides) for _ in range(count))


def roll_evade(attacker, target, base: int = 50) -> bool:
    """Return ``True`` if ``target`` evades an attack from ``attacker``."""

    evade = state_manager.get_effective_stat(target, "evasion")
    acc = state_manager.get_effective_stat(attacker, "hit_chance")
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
    acc = state_manager.get_effective_stat(attacker, "hit_chance")
    chance = max(0, min(95, base + block - acc))
    roll = random.randint(1, 100)
    result = roll <= chance
    logger.debug("block roll=%s chance=%s result=%s", roll, chance, result)
    return result


def roll_parry(attacker, target, base: int = 0) -> bool:
    """Return ``True`` if ``target`` parries an attack from ``attacker``."""

    parry = state_manager.get_effective_stat(target, "parry_rate")
    acc = state_manager.get_effective_stat(attacker, "hit_chance")
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
    attempt: bool = False,
) -> str:
    """Return a standardized combat log message with color coding."""

    a_name = getattr(actor, "key", str(actor))
    t_name = getattr(target, "key", str(target))

    if attempt:
        return f"{a_name} {action} {t_name}."

    if miss:
        return f"|C{a_name}'s {action} misses {t_name}!|n"

    if damage is not None:
        # Estimate the maximum possible damage for color coding
        max_damage = state_manager.get_effective_stat(actor, "attack_power")
        if not max_damage:
            level = getattr(getattr(actor, "db", None), "level", 0) or 0
            max_damage = level * 5
        max_damage = max(max_damage, 1)

        if damage >= 0.9 * max_damage:
            color = "|R"
        elif damage >= 0.6 * max_damage:
            color = "|r"
        elif damage >= 0.3 * max_damage:
            color = "|y"
        elif damage > 0:
            color = "|g"
        else:
            color = "|w"

        crit_text = " |y(critical)|n" if crit else ""
        return f"{a_name} {action} {t_name} for {color}{damage}|n damage{crit_text}"

    return f"{a_name} {action} {t_name}!"


def highlight_keywords(text: str) -> str:
    """Wrap common combat phrases in ANSI color codes."""

    if not text:
        return text

    # Only colorize "misses" if it is not already color coded
    text = re.sub(r"(?<!\|C)misses", "|Cmisses|n", text)

    text = text.replace("Critical hit!", "|RCritical hit!|n")
    return text


def get_condition_msg(hp: int, max_hp: int) -> str:
    """Return a short description of current health."""

    percent = hp * 100 // max_hp if max_hp else 0
    if percent >= 95:
        return "is in excellent condition."
    if percent >= 80:
        return "has a few scratches."
    if percent >= 60:
        return "has some wounds."
    if percent >= 40:
        return "has nasty wounds."
    if percent >= 20:
        return "is bleeding badly."
    if percent > 0:
        return "is in awful condition."
    return "is dead."
