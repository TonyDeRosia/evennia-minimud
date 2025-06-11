"""Predefined NPC templates with baseline stats and flags."""

from copy import deepcopy

MOB_TEMPLATES = {
    "warrior": {
        "level": 1,
        "combat_class": "Warrior",
        "hp": 30,
        "mp": 0,
        "sp": 10,
        "primary_stats": {"STR": 4, "CON": 3, "DEX": 3, "INT": 1, "WIS": 1, "LUCK": 1},
        "actflags": ["aggressive"],
        "skills": ["slash"],
    },
    "caster": {
        "level": 1,
        "combat_class": "Mage",
        "hp": 20,
        "mp": 30,
        "sp": 5,
        "primary_stats": {"STR": 1, "CON": 2, "DEX": 2, "INT": 4, "WIS": 4, "LUCK": 1},
        "spells": ["magic missile"],
        "actflags": ["sentinel"],
    },
}


def get_template(name: str):
    """Return a deep copy of the template dictionary."""
    data = MOB_TEMPLATES.get(name.lower())
    if data:
        return deepcopy(data)
    return None
