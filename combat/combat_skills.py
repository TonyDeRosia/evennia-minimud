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

from combat.combat_actions import CombatResult
from combat.combat_utils import roll_damage, roll_evade
from combat.effects import StatusEffect
from world.system import stat_manager
from world.skills.kick import Kick
from world.skills.disarm import Disarm


@dataclass
class Skill:
    """Base skill definition."""

    name: str
    category: SkillCategory = SkillCategory.MELEE
    damage: tuple[int, int] | None = None
    stamina_cost: int = 0
    cooldown: int = 0
    # Optional skill granting a proficiency bonus to success chance
    support_skill: str | None = None
    effects: List[StatusEffect] = field(default_factory=list)

    def resolve(self, user, target) -> CombatResult:
        return CombatResult(actor=user, target=target, message="Nothing happens.")


class ShieldBash(Skill):
    name = "shield bash"
    support_skill = None
    category = SkillCategory.MELEE
    damage = (2, 6)
    cooldown = 6
    stamina_cost = 15
    effects = [StatusEffect(key="stunned", duration=1, desc="Stunned")]

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
    support_skill = "swords"
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


# Mapping of available skill classes by key
SKILL_CLASSES: Dict[str, type[Skill]] = {
    "shield bash": ShieldBash,
    "cleave": Cleave,
    "kick": Kick,
    "disarm": Disarm,
}
