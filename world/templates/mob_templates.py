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
        "equipment": ["IRON_SWORD", "IRON_HAUBERK", "LEATHER_BOOTS"],
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
        "equipment": ["IRON_DAGGER", "WOOL_TUNIC", "WOOL_LEGGINGS"],
    },
    "merchant": {
        "level": 1,
        "npc_type": "merchant",
        "roles": ["merchant"],
        "ai_type": "passive",
        "actflags": ["sentinel"],
        "equipment": ["WOOL_TUNIC", "WOOL_LEGGINGS"],
        "shop": {
            "buy_percent": 100,
            "sell_percent": 100,
            "hours": "0-24",
            "item_types": ["weapon", "armor"],
        },
        "merchant_markup": 1.0,
    },
}


def get_template(name: str):
    """Return a deep copy of the template dictionary."""
    data = MOB_TEMPLATES.get(name.lower())
    if data:
        return deepcopy(data)
    return None
