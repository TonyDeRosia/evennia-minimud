"""Definitions for basic combat actions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Iterable

from .damage_types import DamageType

from evennia.utils import utils
from world.system import state_manager


@dataclass
class CombatResult:
    """Result of an action being resolved."""

    actor: object
    target: object
    message: str
    damage: int = 0
    damage_type: object | None = None


class Action:
    """Base class for combat actions.

    Actions may define costs and requirements that must be satisfied
    before they can be executed. The :meth:`validate` method performs
    these checks so the :class:`~combat.combat_engine.CombatEngine` can
    decide whether to execute the action or not.
    """

    #: How early in the round the action should resolve. Higher values
    #: execute before lower ones for participants with equal initiative.
    priority: int = 0
    #: Stamina and mana costs for performing the action
    stamina_cost: int = 0
    mana_cost: int = 0
    #: Maximum range in rooms. A value of ``1`` means the target must be
    #: in the same location as the actor.
    range: int = 1
    #: Statuses the actor must have to execute the action
    requires_status: Iterable[str] | None = None

    def __init__(self, actor: object, target: Optional[object] = None):
        """Initialize the action with its actor and optional target.

        Parameters
        ----------
        actor
            Character performing the action.
        target
            Object the action is aimed at, if any.
        """
        self.actor = actor
        self.target = target

    # -------------------------------------------------------------
    # Validation
    # -------------------------------------------------------------
    def validate(self) -> tuple[bool, str]:
        """Check resources and positioning before execution.

        Returns
        -------
        tuple[bool, str]
            ``True`` and an empty string if valid, otherwise ``False`` and an
            explanatory message.
        """

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
            statuses = (
                [self.requires_status]
                if isinstance(self.requires_status, str)
                else list(self.requires_status)
            )
            for st in statuses:
                if not actor.tags.has(st, category="status"):
                    return False, f"Requires {st}."
        return True, ""

    def resolve(self) -> CombatResult:
        """Execute the action and produce a :class:`CombatResult`."""
        raise NotImplementedError


class AttackAction(Action):
    """Simple weapon attack."""

    priority = 1

    def resolve(self) -> CombatResult:
        """Carry out a basic weapon attack."""
        target = self.target
        if not target:
            return CombatResult(self.actor, self.actor, "No target.")
        weapon = self.actor
        if utils.inherits_from(self.actor, "typeclasses.characters.Character"):
            if self.actor.wielding:
                weapon = self.actor.wielding[0]
            elif getattr(self.actor.db, "natural_weapon", None):
                # use natural weapon stats when unarmed
                weapon = self.actor.db.natural_weapon
            else:
                weapon = self.actor
        dmg = 0
        dtype = DamageType.BLUDGEONING
        if hasattr(target, "hp"):
            if isinstance(weapon, dict):
                dmg = weapon.get("damage", 0)
                dtype = weapon.get("damage_type", DamageType.BLUDGEONING)
            else:
                dmg = getattr(weapon, "damage", 0)
                dtype = getattr(weapon, "damage_type", DamageType.BLUDGEONING)
            # scale damage using attacker stats
            str_val = state_manager.get_effective_stat(self.actor, "STR")
            dex_val = state_manager.get_effective_stat(self.actor, "DEX")
            # Formula: base_damage * (1 + STR*0.012 + DEX*0.004)
            dmg = int(round(dmg * (1 + str_val * 0.012 + dex_val * 0.004)))
        return CombatResult(
            actor=self.actor,
            target=target,
            message=f"{self.actor.key} strikes {target.key} for {dmg} damage!",
            damage=dmg,
            damage_type=dtype,
        )


class DefendAction(Action):
    """Assume a defensive stance to reduce incoming damage."""

    priority = 5

    def resolve(self) -> CombatResult:
        """Enter a defensive stance for one round."""
        state_manager.add_status_effect(self.actor, "defending", 1)
        return CombatResult(
            actor=self.actor,
            target=self.actor,
            message=f"{self.actor.key} braces defensively.",
        )


class SkillAction(Action):
    """Use a :class:`~combat.combat_skills.Skill` against a target."""

    priority = 3

    def __init__(self, actor: object, skill, target: Optional[object] = None):
        """Create an action that executes ``skill``.

        Parameters
        ----------
        actor
            Character using the skill.
        skill
            Skill object providing the :py:meth:`resolve` implementation.
        target
            Optional target of the skill.
        """
        super().__init__(actor, target)
        self.skill = skill
        self.stamina_cost = getattr(skill, "stamina_cost", 0)

    def resolve(self) -> CombatResult:
        """Execute the skill and return its result."""
        if self.stamina_cost and hasattr(self.actor.traits, "stamina"):
            self.actor.traits.stamina.current -= self.stamina_cost
        return self.skill.resolve(self.actor, self.target)


class SpellAction(Action):
    """Cast a spell at a target."""

    priority = 3

    def __init__(self, actor: object, spell_key: str, target: Optional[object] = None):
        """Create a spell casting action.

        Parameters
        ----------
        actor
            Character casting the spell.
        spell_key
            Key of the spell to look up.
        target
            Optional spell target.
        """
        super().__init__(actor, target)
        from world.spells import SPELLS

        self.spell = SPELLS.get(spell_key)
        if self.spell:
            self.mana_cost = self.spell.mana_cost

    def resolve(self) -> CombatResult:
        """Invoke the stored spell and return its combat result."""
        if not self.spell:
            return CombatResult(self.actor, self.target or self.actor, "Nothing happens.")
        if self.mana_cost and hasattr(self.actor.traits, "mana"):
            self.actor.traits.mana.current -= self.mana_cost
        success = getattr(self.actor, "cast_spell", None)
        if callable(success):
            success(self.spell.key, self.target)
        return CombatResult(
            actor=self.actor,
            target=self.target or self.actor,
            message=f"{self.actor.key} casts {self.spell.key}!",
        )
