"""Definitions for basic combat actions."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional, Iterable

from .engine.combat_math import CombatMath
from .combat_utils import format_combat_message
from world.system import state_manager
from world.abilities import colorize_name, use_skill, cast_spell

logger = logging.getLogger(__name__)


@dataclass
class CombatResult:
    """Result of an action being resolved."""
    actor: object
    target: object
    message: str
    damage: int = 0
    damage_type: object | None = None


class Action:
    """Base class for combat actions."""
    priority: int = 0
    stamina_cost: int = 0
    mana_cost: int = 0
    range: int = 1
    requires_status: Iterable[str] | None = None

    def __init__(self, actor: object, target: Optional[object] = None):
        self.actor = actor
        self.target = target

    def validate(self) -> tuple[bool, str]:
        actor = self.actor
        traits = getattr(actor, "traits", None)

        if self.stamina_cost and traits and hasattr(traits, "stamina"):
            if traits.stamina.current < self.stamina_cost:
                return False, "Not enough stamina."
        if self.mana_cost and traits and hasattr(traits, "mana"):
            if traits.mana.current < self.mana_cost:
                return False, "Not enough mana."
        if (
            self.range == 1
            and self.target
            and getattr(actor, "location", None) is not getattr(self.target, "location", None)
        ):
            return False, "Target out of range."
        if self.requires_status and hasattr(actor, "tags"):
            statuses = [self.requires_status] if isinstance(self.requires_status, str) else list(self.requires_status)
            for st in statuses:
                if not actor.tags.has(st, category="status"):
                    return False, f"Requires {st}."
        return True, ""

    def resolve(self) -> CombatResult:
        raise NotImplementedError


class AttackAction(Action):
    """Simple weapon attack."""
    priority = 1

    def resolve(self) -> CombatResult:
        target = self.target
        if not target:
            return CombatResult(self.actor, self.actor, "No target.")

        weapon_getter = getattr(self.actor, "get_attack_weapon", None)
        weapon = weapon_getter() if callable(weapon_getter) else self.actor

        logger.debug("AttackAction weapon=%s", getattr(weapon, "key", weapon))
        wname = getattr(weapon, "key", None) or (weapon.get("name") if isinstance(weapon, dict) else "fists")

        attempt = format_combat_message(
            self.actor, target, f"swings {wname} at", attempt=True
        )

        unarmed = not getattr(self.actor, "wielding", [])
        hit_bonus = 0.0
        if unarmed:
            from world.skills.unarmed_passive import Unarmed
            from world.skills.hand_to_hand import HandToHand
            for cls in (Unarmed, HandToHand):
                if cls.name in (self.actor.db.skills or []):
                    cls().improve(self.actor)
            chance = CombatMath.calculate_unarmed_hit(self.actor)
            hit_bonus = chance - 85

        hit, outcome = CombatMath.check_hit(self.actor, target, bonus=hit_bonus)
        if not hit:
            return CombatResult(self.actor, target, f"{attempt}\n{outcome}")

        dmg, dtype = CombatMath.calculate_damage(self.actor, weapon, target)
        dmg, crit = CombatMath.apply_critical(self.actor, target, dmg)

        msg = format_combat_message(
            self.actor, target, "hits", dmg, crit=crit
        )

        return CombatResult(
            self.actor, target, f"{attempt}\n{msg}", damage=dmg, damage_type=dtype
        )


class DefendAction(Action):
    """Assume a defensive stance."""
    priority = 5

    def resolve(self) -> CombatResult:
        state_manager.add_status_effect(self.actor, "defending", 1)
        return CombatResult(self.actor, self.actor, f"{self.actor.key} braces defensively.")


class SkillAction(Action):
    """Use a skill against a target."""
    priority = 3

    def __init__(self, actor: object, skill, target: Optional[object] = None):
        super().__init__(actor, target)
        self.skill = skill
        self.stamina_cost = getattr(skill, "stamina_cost", 0)

    def resolve(self) -> CombatResult:
        if self.stamina_cost and hasattr(self.actor.traits, "stamina"):
            self.actor.traits.stamina.current -= self.stamina_cost
        result = use_skill(self.actor, self.target, self.skill.name)
        if result is None:
            return CombatResult(self.actor, self.target or self.actor, "Nothing happens.")
        if result.message:
            result.message = result.message.replace(self.skill.name, colorize_name(self.skill.name))
        if result.damage:
            result.damage, crit = CombatMath.apply_critical(self.actor, result.target, result.damage)
            if crit:
                result.message += "\nCritical hit!"
        return result


class SpellAction(Action):
    """Cast a spell at a target."""
    priority = 3

    def __init__(self, actor: object, spell_key: str, target: Optional[object] = None):
        super().__init__(actor, target)
        from world.spells import SPELLS
        self.spell = SPELLS.get(spell_key)
        if self.spell:
            self.mana_cost = self.spell.mana_cost

    def resolve(self) -> CombatResult:
        if not self.spell:
            return CombatResult(self.actor, self.target or self.actor, "Nothing happens.")

        result = cast_spell(self.actor, self.spell.key, target=self.target)
        if result.message:
            result.message = f"{self.actor.key} casts {colorize_name(self.spell.key)}!\n" + result.message
        if result.damage:
            result.damage, crit = CombatMath.apply_critical(self.actor, result.target, result.damage)
            if crit:
                result.message += "\nCritical hit!"
        return result
