"""Engine subpackage for combat components."""

from ..combatants import _current_hp, CombatParticipant
from .turn_manager import TurnManager
from ..aggro_tracker import AggroTracker
from ..damage_processor import DamageProcessor
from .. import damage_processor as damage_processor
from .combat_math import CombatMath
from .combat_engine import CombatEngine
import sys

sys.modules[__name__ + ".damage_processor"] = damage_processor

__all__ = [
    "CombatEngine",
    "TurnManager",
    "AggroTracker",
    "DamageProcessor",
    "CombatMath",
    "CombatParticipant",
    "_current_hp",
]

