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
    "Warrior": {1: ["kick", "recall"], 2: ["cleave"], 3: ["shield bash"]},
    "Mystic": {1: ["kick", "recall"]},
    "Wizard": {1: ["kick", "recall"]},
    "Sorcerer": {1: ["kick", "recall"]},
    "Mage": {1: ["kick", "recall"]},
    "Battlemage": {1: ["kick", "recall"]},
    "Necromancer": {1: ["kick", "recall"]},
    "Spellbinder": {1: ["kick", "recall"]},
    "Priest": {1: ["kick", "recall"]},
    "Paladin": {1: ["kick", "recall"]},
    "Druid": {1: ["kick", "recall"]},
    "Shaman": {1: ["kick", "recall"]},
    "Rogue": {1: ["kick", "recall"]},
    "Ranger": {1: ["kick", "recall"]},
    "Warlock": {1: ["kick", "recall"]},
    "Bard": {1: ["kick", "recall"]},
    "Swashbuckler": {1: ["kick", "recall"]},
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

