"""Class skill progression definitions."""

from __future__ import annotations

from typing import Dict, List

# Classes considered melee-oriented for granting Hand-to-Hand.
MELEE_CLASSES = {
    "Warrior",
    "Paladin",
    "Rogue",
    "Ranger",
    "Swashbuckler",
    "Battlemage",
    "Mystic",
}

# Mapping of class names to level->skills lists
CLASS_SKILLS: Dict[str, Dict[int, List[str]]] = {
    "Warrior": {1: ["kick"], 2: ["cleave"], 3: ["shield bash"]},
    "Mystic": {1: ["kick"]},
    "Wizard": {1: ["kick"]},
    "Sorcerer": {1: ["kick"]},
    "Mage": {1: ["kick"]},
    "Battlemage": {1: ["kick"]},
    "Necromancer": {1: ["kick"]},
    "Spellbinder": {1: ["kick"]},
    "Priest": {1: ["kick"]},
    "Paladin": {1: ["kick"]},
    "Druid": {1: ["kick"]},
    "Shaman": {1: ["kick"]},
    "Rogue": {1: ["kick"]},
    "Ranger": {1: ["kick"]},
    "Warlock": {1: ["kick"]},
    "Bard": {1: ["kick"]},
    "Swashbuckler": {1: ["kick"]},
}


def get_class_skills(charclass: str, level: int) -> List[str]:
    """Return skills granted to ``charclass`` up to ``level``."""
    if level <= 0:
        return []
    skills: List[str] = []
    table = CLASS_SKILLS.get(charclass)
    if not table:
        return skills
    for lvl in sorted(table):
        if lvl > level:
            break
        skills.extend(table[lvl])
    return list(dict.fromkeys(skills))


__all__ = ["CLASS_SKILLS", "get_class_skills", "MELEE_CLASSES"]

