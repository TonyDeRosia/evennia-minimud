from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple, List

__all__ = ["HitLocation", "Limb", "DEFAULT_HIT_LOCATIONS"]


@dataclass(frozen=True)
class HitLocation:
    """Location on a body that can be struck."""

    name: str
    damage_mod: float = 1.0


@dataclass(frozen=True)
class Limb:
    """Collection of hit locations representing a limb."""

    name: str
    locations: Tuple[HitLocation, ...]


# Basic humanoid layout used by default combat routines
HEAD = HitLocation("head", damage_mod=1.5)
TORSO = HitLocation("torso", damage_mod=1.0)
ARM = HitLocation("arm", damage_mod=0.8)
LEG = HitLocation("leg", damage_mod=0.8)

DEFAULT_HIT_LOCATIONS: List[HitLocation] = [HEAD, TORSO, ARM, LEG]
