"""Definitions of combat skills and abilities."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, TYPE_CHECKING
import random

from .combat_utils import roll_damage, roll_evade, format_combat_message, highlight_keywords
from .combat_states import CombatState
from world.system import stat_manager
from world.skills.kick import Kick

if TYPE_CHECKING:  # pragma: no cover
    from .combat_actions import CombatResult


class SkillCategory(str, Enum):
    """Categories for skills."""
    MELEE = "melee"
    RANGED = "ranged"
    MAGIC = "magic"


@dataclass
class Skill:
    """Base skill definition."""

    name: str
    category: SkillCategory = SkillCategory.MELEE
    damage: tuple[int, int] | None = None
    stamina_cost: int = 0
    cooldown: int = 0
    effects: List[CombatState] = field(default_factory=list)

    def resolve(self, user, target) -> "CombatResult":
        from .combat_actions import CombatResult
        return CombatResult(actor=user, target=target, message="Nothing happens.")


class ShieldBash(Skill):
    name = "shield bash"
    category = SkillCategory.MELEE
    damage = (2, 6)
    cooldown = 6
    stamina_cost = 15
    effects = [CombatState(key="stunned", duration=1, desc="Stunned")]

    def resolve(self, user, target):
        from .combat_actions import CombatResult
        if not getattr(target, "is_alive", lambda: True)():
            return CombatResult(actor=user, target=target, message="They are already down.")

        if not stat_manager.check_hit(user, target):
            msg = format_combat_message(user, target, "shield bash", miss=True)
            return CombatResult(actor=user, target=target, message=highlight_keywords(msg))

        if roll_evade(user, target):
            msg = format_combat_message(user, target, "shield bash", miss=True)
            return CombatResult(actor=user, target=target, message=highlight_keywords(msg))

        dmg = roll_damage(self.damage)
        target.hp = max(target.hp - dmg, 0)
        msg = f"{user.key} slams {target.key} with a shield, stunning them!"
        return CombatResult(actor=user, target=target, message=highlight_keywords(msg))


class Thrust(Skill):
    name = "thrust"
    category = SkillCategory.MELEE
    damage = (3, 6)
    cooldown = 6
    stamina_cost = 15

    def resolve(self, user, target):
        from .combat_actions import CombatResult
        if not getattr(target, "is_alive", lambda: True)():
            return CombatResult(actor=user, target=target, message="They are already down.")

        if not stat_manager.check_hit(user, target):
            msg = format_combat_message(user, target, "thrust", miss=True)
            return CombatResult(actor=user, target=target, message=highlight_keywords(msg))

        if roll_evade(user, target):
            msg = format_combat_message(user, target, "thrust", miss=True)
            return CombatResult(actor=user, target=target, message=highlight_keywords(msg))

        dmg = roll_damage(self.damage)
        target.hp = max(target.hp - dmg, 0)
        msg = format_combat_message(user, target, "thrusts", dmg)
        return CombatResult(actor=user, target=target, message=highlight_keywords(msg))


class Cleave(Skill):
    name = "cleave"
    category = SkillCategory.MELEE
    damage = (3, 6)
    cooldown = 8
    stamina_cost = 20

    def resolve(self, user, target):
        from .combat_actions import CombatResult
        location = getattr(user, "location", None)
        if not location:
            return CombatResult(actor=user, target=user, message="You're nowhere.")

        room_targets = [
            obj for obj in location.contents
            if obj != user and hasattr(obj, "is_alive") and obj.is_alive()
        ]
        if not room_targets:
            return CombatResult(actor=user, target=user, message="No enemies nearby.")

        selected = random.sample(room_targets, min(len(room_targets), random.randint(1, 3)))
        messages = []

        for t in selected:
            if not stat_manager.check_hit(user, t) or roll_evade(user, t):
                msg = format_combat_message(user, t, "cleave", miss=True)
                messages.append(highlight_keywords(msg))
                continue

            dmg = roll_damage(self.damage)
            t.hp = max(t.hp - dmg, 0)
            msg = format_combat_message(user, t, "cleaves", dmg)
            messages.append(highlight_keywords(msg))

        return CombatResult(actor=user, target=user, message="\n".join(messages))


# Mapping of available skill classes by key
SKILL_CLASSES: Dict[str, type[Skill]] = {
    "shield bash": ShieldBash,
    "thrust": Thrust,
    "cleave": Cleave,
    "kick": Kick,
}
