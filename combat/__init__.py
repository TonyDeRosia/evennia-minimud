"""Combat system package."""

from .combat_engine import CombatEngine
from .combat_actions import (
    Action,
    AttackAction,
    DefendAction,
    SkillAction,
    SpellAction,
    CombatResult,
)
from .combat_states import CombatState, StateManager
from .combat_skills import Skill, ShieldBash, Cleave, SKILL_CLASSES
from .damage_types import DamageType

__all__ = [
    "CombatEngine",
    "Action",
    "AttackAction",
    "DefendAction",
    "SkillAction",
    "SpellAction",
    "CombatResult",
    "CombatState",
    "StateManager",
    "Skill",
    "ShieldBash",
    "Cleave",
    "SKILL_CLASSES",
    "DamageType",
]
