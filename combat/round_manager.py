"""Deprecated combat round management module.

This file now re-exports classes from :mod:`combat.combat_manager`.
"""

from .combat_manager import CombatInstance, CombatRoundManager, leave_combat

__all__ = ["CombatInstance", "CombatRoundManager", "leave_combat"]
