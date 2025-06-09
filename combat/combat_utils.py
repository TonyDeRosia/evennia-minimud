"""Utility helpers for combat."""

import random
from typing import Tuple

from world.system import state_manager


def roll_damage(dice: Tuple[int, int]) -> int:
    """Roll NdN style damage."""
    count, sides = dice
    return sum(random.randint(1, sides) for _ in range(count))


def check_hit(attacker, target, bonus: int = 0) -> bool:
    """Determine if attacker hits target."""
    attack = state_manager.get_effective_stat(attacker, "accuracy") + bonus
    defense = state_manager.get_effective_stat(target, "dodge")
    return random.randint(1, 20) + attack >= 10 + defense
