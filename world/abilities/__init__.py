"""Ability registry and convenience imports."""

from .base import Ability
from .bash import Bash

ABILITY_REGISTRY = {
    Bash.name: Bash,
}

__all__ = ["Ability", "Bash", "ABILITY_REGISTRY"]
