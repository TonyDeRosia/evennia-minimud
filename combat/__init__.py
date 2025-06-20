"""Combat system package."""

from .engine import CombatEngine
from .round_manager import CombatRoundManager, CombatInstance
from .combat_actions import (
    Action,
    AttackAction,
    DefendAction,
    SkillAction,
    SpellAction,
    CombatResult,
)
from .effects import StatusEffect, EffectManager
from .skills import Skill, ShieldBash, Cleave, SKILL_CLASSES
from .damage_types import DamageType
from .combat_utils import get_condition_msg, calculate_initiative
from .action_resolvers import resolve_combat_result

__all__ = [
    "CombatEngine",
    "Action",
    "AttackAction",
    "DefendAction",
    "SkillAction",
    "SpellAction",
    "CombatResult",
    "StatusEffect",
    "EffectManager",
    "Skill",
    "ShieldBash",
    "Cleave",
    "SKILL_CLASSES",
    "DamageType",
    "get_condition_msg",
    "calculate_initiative",
    "CombatRoundManager",
    "CombatInstance",
    "resolve_combat_result",
]
