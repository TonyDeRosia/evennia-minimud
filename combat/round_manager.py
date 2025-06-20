"""Deprecated combat round management module.

``CombatRoundManager`` now lives in :mod:`combat.combat_manager`. This
module simply re-exports the classes for backward compatibility.
"""

from .combat_manager import CombatInstance, CombatRoundManager, leave_combat

__all__ = ["CombatInstance", "CombatRoundManager", "leave_combat"]
