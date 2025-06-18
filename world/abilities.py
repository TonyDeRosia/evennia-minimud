"""Combat ability helpers for casting spells and using skills."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from random import randint
from typing import Optional

from django.conf import settings
from evennia.utils import logger

from combat.combat_skills import SKILL_CLASSES, SkillCategory
from world.spells import SPELLS, Spell
from world.system import state_manager
from utils.ansi_utils import format_ansi_title

__all__ = ["colorize_name", "use_skill", "cast_spell"]

_COLOR_PREFIX = (
    "|r", "|R", "|g", "|G", "|b", "|B", "|y", "|Y",
    "|m", "|M", "|c", "|C", "|w", "|W"
)

_CATEGORY_STAT = {
    SkillCategory.MELEE: "STR",
    SkillCategory.RANGED: "DEX",
    SkillCategory.MAGIC: "INT",
}

logger = logging.getLogger(__name__)


def colorize_name(name: str, color: str = "c") -> str:
    """
    Wrap name in ANSI color codes if not already styled.
    Uses cyan by default and capitalizes name via format_ansi_title.
    """
    if not name:
        return ""
    for prefix in _COLOR_PREFIX:
        if name.startswith(prefix):
            return name if name.endswith("|n") else name + "|n"
    return f"|{color}{format_ansi_title(name)}|n"


def _calc_hit(prof: int, stat_val: int) -> int:
    bonus = max((stat_val - 10) * 0.5, 0)
    return int(round(prof + bonus))


def use_skill(actor, target, skill_name: str) -> CombatResult:
    """
    Execute a skill from actor against target.
    Falls back to actor.use_skill if defined.
    """
    from combat.combat_actions import CombatResult
    use_fn = getattr(actor, "use_skill", None)
    if callable(use_fn):
        return use_fn(skill_name, target=target)

    skill_cls = SKILL_CLASSES.get(skill_name)
    if not skill_cls:
        return CombatResult(actor, target, "Nothing happens.")

    skill = skill_cls()
    if not actor.cooldowns.ready(skill.name):
        return CombatResult(actor, actor, "Still recovering.")
    if actor.traits.stamina.current < skill.stamina_cost:
        return CombatResult(actor, actor, "Too exhausted.")

    prof = (actor.db.proficiencies or {}).get(skill.name, 0)
    stat_key = _CATEGORY_STAT.get(getattr(skill, "category", SkillCategory.MELEE), "STR")
    stat_val = state_manager.get_effective_stat(actor, stat_key)
    hit_chance = _calc_hit(prof, stat_val)
    hit_roll = randint(1, 100)

    actor.traits.stamina.current -= skill.stamina_cost
    state_manager.add_cooldown(actor, skill.name, skill.cooldown)

    if hit_roll > hit_chance:
        msg = f"{colorize_name(actor.key)}'s {skill.name} misses {colorize_name(target.key)}."
        if getattr(settings, "COMBAT_SHOW_HIT", False):
            msg += f" [HIT {hit_chance}%]"
        return CombatResult(actor, target, msg)

    result = skill.resolve(actor, target)
    if getattr(settings, "COMBAT_SHOW_HIT", False):
        result.message += f" [HIT {hit_chance}%]"
    for eff in getattr(skill, "effects", []):
        state_manager.add_status_effect(target, eff.key, eff.duration)
    return result


def cast_spell(actor, spell_key: str, target: Optional[object] = None) -> CombatResult:
    """
    Cast a spell from actor at target.
    Falls back to actor.cast_spell if defined.
    """
    from combat.combat_actions import CombatResult
    cast_fn = getattr(actor, "cast_spell", None)
    if callable(cast_fn):
        return cast_fn(spell_key, target=target)

    spell = SPELLS.get(spell_key)
    if not spell:
        return CombatResult(actor, target or actor, "Nothing happens.")
    if not actor.cooldowns.ready(spell.key):
        return CombatResult(actor, actor, "Still recovering.")
    if actor.traits.mana.current < spell.mana_cost:
        return CombatResult(actor, actor, "Too exhausted.")

    prof = 0
    for entry in actor.db.spells or []:
        if isinstance(entry, Spell) and entry.key == spell.key:
            prof = entry.proficiency
            if prof < 100:
                entry.proficiency = min(100, prof + 1)
                actor.db.spells = actor.db.spells
            break
        if isinstance(entry, str) and entry == spell.key:
            srec = Spell(spell.key, spell.stat, spell.mana_cost, spell.desc, 0)
            idx = actor.db.spells.index(entry)
            actor.db.spells[idx] = srec
            actor.db.spells = actor.db.spells
            prof = 0
            break

    stat_val = state_manager.get_effective_stat(actor, spell.stat)
    hit_chance = _calc_hit(prof, stat_val)
    hit_roll = randint(1, 100)

    actor.traits.mana.current -= spell.mana_cost
    state_manager.add_cooldown(actor, spell.key, spell.cooldown)

    tname = colorize_name(target.key) if target else "the area"
    aname = colorize_name(actor.key)
    hit = hit_roll <= hit_chance

    if hit:
        msg = f"{aname} casts {spell.key} at {tname}!"
    else:
        msg = f"{aname} casts {spell.key} at {tname}, but it fizzles."

    if getattr(settings, "COMBAT_SHOW_HIT", False):
        msg += f" [HIT {hit_chance}%]"

    if not actor.has_account:
        logger.info(f"NPC {actor.key} casts {spell.key} -> {'hit' if hit else 'miss'}")

    if not hit:
        return CombatResult(actor, target or actor, msg)

    return CombatResult(actor, target or actor, msg)
