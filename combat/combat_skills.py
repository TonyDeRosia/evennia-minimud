"""Definitions of combat skills and abilities."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from .combat_actions import CombatResult
from .combat_utils import roll_damage, check_hit
from .combat_states import CombatState


@dataclass
class Skill:
    """Base skill definition."""

    name: str
    damage: tuple[int, int] | None = None
    stamina_cost: int = 0
    cooldown: int = 0
    effects: List[CombatState] = field(default_factory=list)

    def resolve(self, user, target) -> CombatResult:
        return CombatResult(actor=user, target=target, message="Nothing happens.")


class ShieldBash(Skill):
    name = "shield bash"
    damage = (2, 6)
    cooldown = 6
    stamina_cost = 15
    effects = [CombatState(key="stunned", duration=1, desc="Stunned")]

    def resolve(self, user, target):
        if not getattr(target, "is_alive", lambda: True)():
            return CombatResult(actor=user, target=target, message="They are already down.")
        hit = check_hit(user, target)
        if hit:
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
