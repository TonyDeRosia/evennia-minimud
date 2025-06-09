"""Enumerations and helper functions for mob-related data."""

from __future__ import annotations

from enum import Enum
from typing import Iterable, Set


class _StrEnum(str, Enum):
    """Enum with string values supporting case-insensitive comparison."""

    @classmethod
    def from_str(cls, value: str) -> "_StrEnum":
        for member in cls:
            if member.value.lower() == value.lower() or member.name.lower() == value.lower():
                return member
        raise ValueError(value)


class NPC_RACES(_StrEnum):
    HUMAN = "human"
    ELF = "elf"
    TABAXI = "tabaxi"
    LIZARDFOLK = "lizardfolk"
    KITSUNE = "kitsune"
    HALFLING = "halfling"
    DWARF = "dwarf"
    ORC = "orc"
    OGRE = "ogre"
    BIRDFOLK = "birdfolk"
    PIXIE = "pixie"
    MINOTAUR = "minotaur"
    SATYR = "satyr"


class NPC_CLASSES(_StrEnum):
    WARRIOR = "warrior"
    MYSTIC = "mystic"
    WIZARD = "wizard"
    SORCERER = "sorcerer"
    MAGE = "mage"
    BATTLEMAGE = "battlemage"
    NECROMANCER = "necromancer"
    SPELLBINDER = "spellbinder"
    PRIEST = "priest"
    PALADIN = "paladin"
    DRUID = "druid"
    SHAMAN = "shaman"
    ROGUE = "rogue"
    RANGER = "ranger"
    WARLOCK = "warlock"
    BARD = "bard"
    SWASHBUCKLER = "swashbuckler"


class ACTFLAGS(_StrEnum):
    SENTINEL = "sentinel"
    SCAVENGER = "scavenger"
    AGGRESSIVE = "aggressive"
    STAY_AREA = "stay_area"
    WIMPY = "wimpy"


class AFFECTED_BY(_StrEnum):
    BLIND = "blind"
    INVISIBLE = "invisible"
    DETECT_EVIL = "detect_evil"
    DETECT_INVIS = "detect_invis"
    DETECT_MAGIC = "detect_magic"
    DETECT_HIDDEN = "detect_hidden"
    WATERWALK = "waterwalk"
    SANCTUARY = "sanctuary"
    FAERIE_FIRE = "faerie_fire"
    INFRARED = "infrared"
    CURSE = "curse"
    POISON = "poison"
    FLYING = "fly"


class LANGUAGES(_StrEnum):
    COMMON = "common"
    ELVISH = "elvish"
    DWARVISH = "dwarvish"
    ORCISH = "orcish"


class BODYPARTS(_StrEnum):
    HEAD = "head"
    ARMS = "arms"
    LEGS = "legs"
    HEART = "heart"
    BRAIN = "brain"
    GUTS = "guts"
    HANDS = "hands"
    FEET = "feet"
    FINGERS = "fingers"
    EARS = "ears"
    EYES = "eyes"
    LONG_TONGUE = "long_tongue"
    EYESTALKS = "eyestalks"
    TENTACLES = "tentacles"


class SAVING_THROWS(_StrEnum):
    POISON = "poison"
    MAGIC = "magic"
    PARA = "para"
    BREATH = "breath"
    SPELL = "spell"


class RIS_TYPES(_StrEnum):
    FIRE = "fire"
    COLD = "cold"
    ELECTRIC = "electric"
    ENERGY = "energy"
    BLUNT = "blunt"
    PIERCE = "pierce"
    SLASH = "slash"
    ACID = "acid"
    POISON = "poison"
    DRAIN = "drain"
    SLEEP = "sleep"
    CHARM = "charm"
    HOLD = "hold"
    NONMAGIC = "nonmagic"
    PLUS1 = "plus1"


class ATTACK_TYPES(_StrEnum):
    BITE = "bite"
    CLAW = "claw"
    STING = "sting"
    WHIP = "whip"
    SLASH = "slash"
    BLAST = "blast"
    PUNCH = "punch"
    KICK = "kick"


class DEFENSE_TYPES(_StrEnum):
    PARRY = "parry"
    DODGE = "dodge"
    BLOCK = "block"
    ABSORB = "absorb"


class SPECIAL_FUNCS(_StrEnum):
    BREATH_FIRE = "spec_breath_fire"
    CAST_MAGE = "spec_cast_mage"
    CAST_CLERIC = "spec_cast_cleric"
    TOWN_CRIER = "spec_town_crier"


# ------------------------------------------------------------
# Helper functions
# ------------------------------------------------------------

def parse_flag_list(text: str, enum_cls: type[_StrEnum]) -> Set[_StrEnum]:
    """Return a set of enum members from ``text``."""
    flags: Set[_StrEnum] = set()
    for part in text.split():
        member = enum_cls.from_str(part)
        flags.add(member)
    return flags


def flags_to_string(flags: Iterable[_StrEnum]) -> str:
    """Return a space-separated string from ``flags``."""
    return " ".join(flag.value for flag in flags)


__all__ = [
    "NPC_RACES",
    "NPC_CLASSES",
    "ACTFLAGS",
    "AFFECTED_BY",
    "LANGUAGES",
    "BODYPARTS",
    "SAVING_THROWS",
    "RIS_TYPES",
    "ATTACK_TYPES",
    "DEFENSE_TYPES",
    "SPECIAL_FUNCS",
    "parse_flag_list",
    "flags_to_string",
]
