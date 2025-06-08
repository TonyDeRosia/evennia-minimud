"""Mixin classes for specialized NPC behaviors."""

from .merchant import MerchantRole
from .banker import BankerRole
from .trainer import TrainerRole

__all__ = ["MerchantRole", "BankerRole", "TrainerRole"]
