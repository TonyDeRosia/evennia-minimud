from dataclasses import dataclass
from typing import Dict

@dataclass
class Spell:
    """Data describing a castable spell."""

    key: str
    stat: str
    mana_cost: int
    desc: str = ""
    cooldown: int = 0
    # Optional skill providing a proficiency bonus to casting success
    support_skill: str | None = None


SPELLS: Dict[str, Spell] = {
    "fireball": Spell(
        "fireball",
        "INT",
        10,
        "Hurl a ball of fire at your target.",
        cooldown=5,
        support_skill="spellcasting",
    ),
    "heal": Spell(
        "heal",
        "WIS",
        8,
        "Restore a small amount of health.",
        cooldown=3,
        support_skill="spellcasting",
    ),
}


def colorize_spell(name: str) -> str:
    """Return ``name`` wrapped in an ANSI color based on keywords."""

    lname = name.lower()
    if any(key in lname for key in ("fire", "flame", "burn")):
        color = "|r"
    elif any(key in lname for key in ("ice", "frost", "cold")):
        color = "|c"
    elif any(key in lname for key in ("nature", "druid", "plant")):
        color = "|g"
    elif any(key in lname for key in ("necrom", "shadow")):
        color = "|m"
    elif any(key in lname for key in ("holy", "heal", "light")):
        color = "|w"
    else:
        color = "|M"
    return f"{color}{name}|n"
