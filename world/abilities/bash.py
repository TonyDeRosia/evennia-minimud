"""Example ability implementation."""

from typing import Any

from .base import Ability


class Bash(Ability):
    """Simple melee ability used for demonstration."""

    name = "bash"
    level_required = 1
    cooldown = 5
    cost = 10
    description = "Strike the target with a heavy bash."

    def apply(self, user: Any, target: Any) -> str:
        """Apply the bash effect to ``target``."""
        return f"{getattr(user, 'key', user)} bashes {getattr(target, 'key', target)}!"

    def calculate_power(self, user: Any) -> int:
        """Damage is based on the user's level by default."""
        return getattr(user, "level", 1)
