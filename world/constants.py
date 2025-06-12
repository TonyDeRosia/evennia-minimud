"""Shared race and class definitions used across the game."""

from __future__ import annotations

from enum import Enum


class StrEnum(str, Enum):
    """Enum with case-insensitive lookup helper."""

    @classmethod
    def from_str(cls, value: str) -> "StrEnum":
        for member in cls:
            if member.value.lower() == value.lower() or member.name.lower() == value.lower():
                return member
        raise ValueError(value)


class NPC_RACES(StrEnum):
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
    UNIQUE = "unique"


class NPC_CLASSES(StrEnum):
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


RACE_LIST = [
    {"name": "Human", "desc": "Versatile and balanced in all aspects.", "stat_mods": {}},
    {
        "name": "Elf",
        "desc": "Graceful and intelligent. Masters of precision and magic.",
        "stat_mods": {"DEX": 2, "INT": 1, "STR": -1},
    },
    {
        "name": "Tabaxi",
        "desc": "Feline agility and reflexes, always curious and fast.",
        "stat_mods": {"DEX": 2, "LUCK": 1, "CON": -1},
    },
    {
        "name": "Lizardfolk",
        "desc": "Cold-blooded survivors with hardened bodies and minds.",
        "stat_mods": {"CON": 2, "STR": 1, "LUCK": -1},
    },
    {
        "name": "Kitsune",
        "desc": "Clever fox-spirits gifted in illusion and charm.",
        "stat_mods": {"INT": 2, "LUCK": 1, "STR": -1},
    },
    {
        "name": "Halfling",
        "desc": "Small, cheerful, and unbelievably lucky.",
        "stat_mods": {"LUCK": 2, "DEX": 1, "CON": -1},
    },
    {
        "name": "Dwarf",
        "desc": "Stout and unwavering, born of stone and steel.",
        "stat_mods": {"CON": 2, "WIS": 1, "DEX": -1},
    },
    {
        "name": "Orc",
        "desc": "Fierce warriors bred for combat and survival.",
        "stat_mods": {"STR": 2, "CON": 1, "INT": -1},
    },
    {
        "name": "Ogre",
        "desc": "Towering brutes with monstrous strength and low cunning.",
        "stat_mods": {"STR": 3, "CON": 1, "DEX": -2},
    },
    {
        "name": "Birdfolk",
        "desc": "Light-framed aerial hunters with sharp instincts.",
        "stat_mods": {"DEX": 2, "WIS": 1, "STR": -1},
    },
    {
        "name": "Pixie",
        "desc": "Tiny arcane pranksters full of speed and spark.",
        "stat_mods": {"INT": 2, "LUCK": 2, "CON": -2},
    },
    {
        "name": "Minotaur",
        "desc": "Bull-headed warriors, disciplined and unstoppable.",
        "stat_mods": {"STR": 3, "CON": 1, "INT": -2},
    },
    {
        "name": "Satyr",
        "desc": "Mischievous revelers full of wit and charm.",
        "stat_mods": {"LUCK": 2, "WIS": 1, "STR": -1},
    },
]


CLASS_LIST = [
    {
        "name": "Warrior",
        "desc": "A frontline tank and melee powerhouse.",
        "stat_mods": {"STR": 2, "CON": 2},
    },
    {
        "name": "Mystic",
        "desc": "A monk who channels spiritual animal forms through martial discipline.",
        "stat_mods": {"WIS": 2, "DEX": 1, "CON": 1},
    },
    {
        "name": "Wizard",
        "desc": "A disciplined scholar of arcane knowledge and raw spell power.",
        "stat_mods": {"INT": 3, "WIS": 1, "CON": -1},
    },
    {
        "name": "Sorcerer",
        "desc": "A natural magic user with wild power and unpredictable force.",
        "stat_mods": {"INT": 2, "LUCK": 1},
    },
    {
        "name": "Mage",
        "desc": "An elemental caster with mastery over both fire and frost.",
        "stat_mods": {"INT": 2, "WIS": 2},
    },
    {
        "name": "Battlemage",
        "desc": "A hybrid fighter-mage, blending swords and sorcery.",
        "stat_mods": {"STR": 1, "INT": 2, "DEX": 1},
    },
    {
        "name": "Necromancer",
        "desc": "Master of undeath, commanding bones and shadows.",
        "stat_mods": {"INT": 2, "WIS": 2, "LUCK": -1},
    },
    {
        "name": "Spellbinder",
        "desc": "Tactical controller with enchantments and traps.",
        "stat_mods": {"INT": 2, "LUCK": 2},
    },
    {
        "name": "Priest",
        "desc": "Wielder of holy light or shadow--healer, protector, or punisher.",
        "stat_mods": {"WIS": 3, "CON": 1},
    },
    {
        "name": "Paladin",
        "desc": "A divine warrior devoted to justice and protection.",
        "stat_mods": {"STR": 2, "WIS": 2},
    },
    {
        "name": "Druid",
        "desc": "A wild shape-shifter bonded with nature's essence.",
        "stat_mods": {"WIS": 2, "CON": 2},
    },
    {
        "name": "Shaman",
        "desc": "A tribal caster channeling elements and spirits.",
        "stat_mods": {"WIS": 2, "INT": 1, "LUCK": 1},
    },
    {
        "name": "Rogue",
        "desc": "A cunning assassin and master of stealth and traps.",
        "stat_mods": {"DEX": 2, "LUCK": 2},
    },
    {
        "name": "Ranger",
        "desc": "Beastmaster and sharpshooter with survival instincts.",
        "stat_mods": {"DEX": 2, "WIS": 2},
    },
    {
        "name": "Warlock",
        "desc": "A forceful wielder of forbidden magic and domination.",
        "stat_mods": {"INT": 2, "LUCK": 2},
    },
    {
        "name": "Bard",
        "desc": "A charismatic performer wielding magic through music and story.",
        "stat_mods": {"LUCK": 2, "INT": 2},
    },
    {
        "name": "Swashbuckler",
        "desc": "A flashy duelist with wit, speed, and bravado.",
        "stat_mods": {"DEX": 2, "LUCK": 2},
    },
]

__all__ = [
    "StrEnum",
    "NPC_RACES",
    "NPC_CLASSES",
    "RACE_LIST",
    "CLASS_LIST",
]
