"""Engine subpackage for combat components."""

from ..combatants import _current_hp, CombatParticipant
from .turn_manager import TurnManager
from ..aggro_tracker import AggroTracker
from ..damage_processor import DamageProcessor
from .combat_math import CombatMath
from .combat_engine import CombatEngine

__all__ = [
    "CombatEngine",
    "TurnManager",
    "AggroTracker",
    "DamageProcessor",
    "CombatMath",
    "CombatParticipant",
    "_current_hp",
]

