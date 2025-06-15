from dataclasses import dataclass
from typing import Any

@dataclass
class Ability:
    """Base class for character abilities."""

    name: str = ""
    level_required: int = 0
    cooldown: int = 0
    cost: int = 0
    description: str = ""

    def apply(self, user: Any, target: Any) -> Any:
        """Apply this ability's effect."""
        raise NotImplementedError

    def calculate_power(self, user: Any) -> int:
        """Return the power of this ability based on ``user``."""
        return 0
