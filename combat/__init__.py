"""Combat system package."""

import os
import django
import evennia

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()
if getattr(evennia, "SESSION_HANDLER", None) is None:
    evennia._init()

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
from .combat_states import CombatState, CombatStateManager
from .combat_skills import (
    Skill,
    ShieldBash,
    Thrust,
    Cleave,
    SKILL_CLASSES,
)
from .damage_types import DamageType
from .combat_utils import get_condition_msg, calculate_initiative

__all__ = [
    "CombatEngine",
    "Action",
    "AttackAction",
    "DefendAction",
    "SkillAction",
    "SpellAction",
    "CombatResult",
    "CombatState",
    "CombatStateManager",
    "Skill",
    "ShieldBash",
    "Thrust",
    "Cleave",
    "SKILL_CLASSES",
    "DamageType",
    "get_condition_msg",
    "calculate_initiative",
    "CombatRoundManager",
    "CombatInstance",
]
