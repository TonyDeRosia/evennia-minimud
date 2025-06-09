"""Definitions for basic combat actions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from evennia.utils import utils
from world.system import state_manager


@dataclass
class CombatResult:
    """Result of an action being resolved."""

    actor: object
    target: object
    message: str


class Action:
    """Base class for combat actions."""

    def __init__(self, actor: object, target: Optional[object] = None):
        self.actor = actor
        self.target = target

    def resolve(self) -> CombatResult:
        raise NotImplementedError


class AttackAction(Action):
    """Simple weapon attack."""

    def resolve(self) -> CombatResult:
        target = self.target
        if not target:
            return CombatResult(self.actor, self.actor, "No target.")
        if utils.inherits_from(self.actor, "typeclasses.characters.Character"):
            weapon = self.actor.wielding[0] if self.actor.wielding else self.actor
            weapon.at_attack(self.actor, target)
        dmg = 0
        if hasattr(target, "hp"):
            dmg = getattr(weapon, "damage", 0)
            target.hp = max(target.hp - dmg, 0)
        return CombatResult(
            actor=self.actor,
            target=target,
            message=f"{self.actor.key} strikes {target.key} for {dmg} damage!",
        )
