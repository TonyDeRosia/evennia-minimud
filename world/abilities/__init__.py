"""Ability registry and convenience imports."""

from .base import Ability
from .bash import Bash
from .ability_table import CLASS_ABILITY_TABLE

ABILITY_REGISTRY = {
    Bash.name: Bash,
}

__all__ = ["Ability", "Bash", "ABILITY_REGISTRY", "CLASS_ABILITY_TABLE"]
