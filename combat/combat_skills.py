"""Definitions of combat skills and abilities."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict


class SkillCategory(str, Enum):
    """Categories for skills."""

    MELEE = "melee"
    RANGED = "ranged"
    MAGIC = "magic"

from .combat_actions import CombatResult
from .combat_utils import roll_damage, roll_evade
from .combat_states import CombatState
from world.system import stat_manager


@dataclass(init=False)
class Skill:
    """Base skill definition used by combat."""

    name: str
    category: SkillCategory = SkillCategory.MELEE
    damage: tuple[int, int] | None = None
    stamina_cost: int = 0
    cooldown: int = 0
    effects: List[CombatState] = field(default_factory=list)

    def __init__(self, *, name: str | None = None, category: SkillCategory | None = None,
                 damage: tuple[int, int] | None = None, stamina_cost: int | None = None,
                 cooldown: int | None = None, effects: List[CombatState] | None = None) -> None:
        """Initialize skill using subclass defaults when arguments are omitted."""
        cls = self.__class__
        self.name = name if name is not None else getattr(cls, "name", "")
        self.category = category if category is not None else getattr(cls, "category", SkillCategory.MELEE)
        self.damage = damage if damage is not None else getattr(cls, "damage", None)
        self.stamina_cost = stamina_cost if stamina_cost is not None else getattr(cls, "stamina_cost", 0)
        self.cooldown = cooldown if cooldown is not None else getattr(cls, "cooldown", 0)
        self.effects = effects if effects is not None else list(getattr(cls, "effects", []))

    def resolve(self, user, target) -> CombatResult:
        return CombatResult(actor=user, target=target, message="Nothing happens.")


class ShieldBash(Skill):
    name = "shield bash"
    category = SkillCategory.MELEE
    damage = (2, 6)
    cooldown = 6
    stamina_cost = 15
    effects = [CombatState(key="stunned", duration=1, desc="Stunned")]

    def resolve(self, user, target):
        if not getattr(target, "is_alive", lambda: True)():
            return CombatResult(actor=user, target=target, message="They are already down.")
        hit = stat_manager.check_hit(user, target)
        if hit:
            if roll_evade(user, target):
                return CombatResult(
                    actor=user,
                    target=target,
                    message=f"{user.key}'s shield bash misses {target.key}.",
                )
            dmg = roll_damage(self.damage)
            target.hp = max(target.hp - dmg, 0)
            return CombatResult(
                actor=user,
                target=target,
                message=f"{user.key} slams {target.key} with a shield, stunning them!",
            )
        else:
            return CombatResult(
                actor=user,
                target=target,
                message=f"{user.key}'s shield bash misses {target.key}.",
            )


class Cleave(Skill):
    """Powerful swing hitting a single foe."""

    name = "cleave"
    category = SkillCategory.MELEE
    damage = (3, 6)
    stamina_cost = 20
    cooldown = 8

    def resolve(self, user, target):
        if not getattr(target, "is_alive", lambda: True)():
            return CombatResult(actor=user, target=target, message="They are already down.")
        if stat_manager.check_hit(user, target):
            if roll_evade(user, target):
                msg = f"{user.key}'s cleave misses {target.key}."
            else:
                dmg = roll_damage(self.damage)
                target.hp = max(target.hp - dmg, 0)
                msg = f"{user.key} cleaves {target.key} for {dmg} damage!"
        else:
            msg = f"{user.key}'s cleave misses {target.key}."
        return CombatResult(actor=user, target=target, message=msg)


class Kick(Skill):
    """Simple unarmed kick scaling with Strength."""

    name = "kick"
    category = SkillCategory.MELEE
    cooldown = 3

    def resolve(self, user, target):
        if not getattr(target, "is_alive", lambda: True)():
            return CombatResult(actor=user, target=target, message="They are already down.")
        if not stat_manager.check_hit(user, target):
            return CombatResult(actor=user, target=target, message=f"{user.key}'s kick misses {target.key}.")
        if roll_evade(user, target):
            return CombatResult(actor=user, target=target, message=f"{target.key} evades {user.key}'s kick.")
        str_val = stat_manager.get_effective_stat(user, "STR")
        dmg = 5 + int(str_val * 0.2)
        trait = getattr(user.traits, "kick", None) or user.traits.get("kick")
        prof = getattr(trait, "proficiency", 0)
        dmg = int(dmg * (1 + prof / 100))
        target.hp = max(target.hp - dmg, 0)
        return CombatResult(
            actor=user,
            target=target,
            message=f"{user.key} kicks {target.key} for {dmg} damage!",
            damage=dmg,
        )


# Mapping of available skill classes by key
SKILL_CLASSES: Dict[str, type[Skill]] = {
    "shield bash": ShieldBash,
    "cleave": Cleave,
    "kick": Kick,
}
