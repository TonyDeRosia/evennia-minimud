"""Class skill progression definitions."""

from __future__ import annotations

from typing import Dict, List

# Mapping of class names to level->skills lists
CLASS_SKILLS: Dict[str, Dict[int, List[str]]] = {
    "Warrior": {
        1: ["kick"],
        2: ["cleave"],
        3: ["shield bash"],
    },
    "Mage": {
        1: ["kick"],
    },
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


__all__ = ["CLASS_SKILLS", "get_class_skills"]

