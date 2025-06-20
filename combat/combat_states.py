"""Deprecated module. Use :mod:`combat.effects` instead."""

from .effects import StatusEffect as CombatState, EffectManager as CombatStateManager

__all__ = ["CombatState", "CombatStateManager"]
