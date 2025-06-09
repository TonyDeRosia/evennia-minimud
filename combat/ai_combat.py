"""Basic combat AI utilities."""

import random

from .combat_actions import AttackAction
from .combat_engine import CombatEngine


def npc_take_turn(engine: CombatEngine, npc, target):
    """Very simple AI to attack target each round."""
    if not target or getattr(target, "hp", 0) <= 0:
        return
    engine.queue_action(npc, AttackAction(npc, target))
