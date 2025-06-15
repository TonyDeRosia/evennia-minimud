"""Ability registry and convenience imports."""

from .base import Ability
from .bash import Bash
from .ability_table import CLASS_ABILITY_TABLE
from .skills.kick import Kick

ABILITY_REGISTRY = {
    Bash.name: Bash,
    Kick.name: Kick,
}

__all__ = [
    "Ability",
    "Bash",
    "Kick",
    "ABILITY_REGISTRY",
    "CLASS_ABILITY_TABLE",
]
