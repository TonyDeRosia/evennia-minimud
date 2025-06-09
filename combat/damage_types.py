"""Damage type constants."""

from enum import Enum


class DamageType(str, Enum):
    SLASHING = "slashing"
    PIERCING = "piercing"
    BLUDGEONING = "bludgeoning"
    FIRE = "fire"
    COLD = "cold"
    ACID = "acid"
    HOLY = "holy"
    SHADOW = "shadow"
    LIGHTNING = "lightning"
    VOID = "void"


class ResistanceType(str, Enum):
    """Types of elemental or physical resistance."""

    SLASHING = "slashing"
    PIERCING = "piercing"
    BLUDGEONING = "bludgeoning"
    FIRE = "fire"
    COLD = "cold"
    ACID = "acid"
    HOLY = "holy"
    SHADOW = "shadow"
    LIGHTNING = "lightning"
    VOID = "void"


RESISTANCE_MATRIX: dict[ResistanceType, dict[DamageType, float]] = {
    ResistanceType.SLASHING: {DamageType.SLASHING: 0.5},
    ResistanceType.PIERCING: {DamageType.PIERCING: 0.5},
    ResistanceType.BLUDGEONING: {DamageType.BLUDGEONING: 0.5},
    ResistanceType.FIRE: {
        DamageType.FIRE: 0.5,
        DamageType.COLD: 1.5,
    },
    ResistanceType.COLD: {
        DamageType.COLD: 0.5,
        DamageType.FIRE: 1.5,
    },
    ResistanceType.ACID: {DamageType.ACID: 0.5},
    ResistanceType.HOLY: {
        DamageType.HOLY: 0.5,
        DamageType.SHADOW: 1.5,
    },
    ResistanceType.SHADOW: {
        DamageType.SHADOW: 0.5,
        DamageType.HOLY: 1.5,
    },
    ResistanceType.LIGHTNING: {
        DamageType.LIGHTNING: 0.5,
        DamageType.VOID: 1.5,
    },
    ResistanceType.VOID: {
        DamageType.VOID: 0.5,
        DamageType.LIGHTNING: 1.5,
    },
}


def get_damage_multiplier(
    resistances: list[ResistanceType] | None, damage_type: DamageType
) -> float:
    """Return the damage multiplier for given resistances and damage type."""

    multiplier = 1.0
    if not resistances:
        return multiplier
    for res in resistances:
        multiplier *= RESISTANCE_MATRIX.get(res, {}).get(damage_type, 1.0)
    return multiplier
