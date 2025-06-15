"""Spell definitions and utilities.

Each :class:`Spell` entry defines how a magical ability behaves.  The new
``cast_type`` attribute determines the command players use to invoke the spell
(usually ``"cast"`` but other values are possible).  All spells are collected
in the :data:`SPELLS` dictionary keyed by name.
"""

from dataclasses import dataclass
from typing import Dict

@dataclass
class Spell:
    key: str
    stat: str
    mana_cost: int
    desc: str = ""
    cooldown: int = 0
    proficiency: int = 0
    cast_type: str = "cast"
    class_type: str = "spell"


SPELLS: Dict[str, Spell] = {
    "fireball": Spell(
        "fireball",
        "INT",
        10,
        "Hurl a ball of fire at your target.",
        cooldown=5,
        cast_type="cast",
    ),
    "heal": Spell(
        "heal",
        "WIS",
        8,
        "Restore a small amount of health.",
        cooldown=3,
        cast_type="cast",
    ),
}
