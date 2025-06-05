# Stat manager for centralizing stat calculations and display

from __future__ import annotations

from typing import Dict
import re

from world import stats
from world.system import state_manager
from world.scripts import races, classes

# Primary and secondary stat keys
PRIMARY_STATS = stats.CORE_STAT_KEYS
SECONDARY_STATS = ["HP", "MP", "SP", "ATK", "DEF", "ACC", "EVA"]

# Mapping of derived stat keys to weighted primary stats
STAT_SCALING: Dict[str, Dict[str, float]] = {
    "HP": {"CON": 10, "STR": 2},
    "MP": {"INT": 10, "WIS": 5},
    "SP": {"CON": 5, "DEX": 5},
    "ATK": {"STR": 2, "DEX": 1},
    "DEF": {"CON": 2},
    "ACC": {"DEX": 1, "LUCK": 0.5},
    "EVA": {"DEX": 1, "LUCK": 0.5},
    # Defense stats
    "armor": {"CON": 1},
    "magic_resist": {"WIS": 1},
    "dodge": {"DEX": 1},
    "block_rate": {"STR": 1},
    "parry_rate": {"DEX": 1},
    "status_resist": {"CON": 1},
    "crit_resist": {"CON": 1},
    # Offense stats
    "attack_power": {"STR": 1},
    "spell_power": {"INT": 1},
    "crit_chance": {"LUCK": 1},
    "crit_bonus": {"STR": 1},
    "accuracy": {"DEX": 1},
    "piercing": {"STR": 1},
    "spell_penetration": {"INT": 1},
    # Regeneration & sustain
    "health_regen": {"CON": 1},
    "mana_regen": {"WIS": 1},
    "stamina_regen": {"CON": 1},
    "lifesteal": {"STR": 1},
    "leech": {"INT": 1},
    # Tempo stats
    "cooldown_reduction": {"WIS": 1},
    "initiative": {"DEX": 1},
    "gcd_speed": {"DEX": 1},
    # Utility stats
    "stealth": {"DEX": 1},
    "detection": {"WIS": 1},
    "perception": {"WIS": 1},
    "threat": {"STR": 1},
    "movement_speed": {"DEX": 1},
    "craft_bonus": {"INT": 1},
    # PvP stats
    "pvp_power": {"STR": 1},
    "pvp_resilience": {"CON": 1},
    "guild_honor_mod": {"WIS": 1},
    # Base evasion skill
    "evasion": {"DEX": 1},
}


# -------------------------------------------------------------
# Bonus collection helpers (stubs for future expansion)
# -------------------------------------------------------------


def _race_mods(obj) -> Dict[str, int]:
    """Return stat modifiers from the character's race."""
    race = getattr(obj.db, "race", None)
    if not race:
        return {}
    for entry in races.RACE_LIST:
        if entry["name"].lower() == str(race).lower():
            return entry.get("stat_mods", {})
    return {}


def _class_mods(obj) -> Dict[str, int]:
    """Return stat modifiers from the character's class."""
    cls = getattr(obj.db, "charclass", None)
    if not cls:
        return {}
    for entry in classes.CLASS_LIST:
        if entry["name"].lower() == str(cls).lower():
            return entry.get("stat_mods", {})
    return {}


def _gear_mods(obj) -> Dict[str, int]:  # pragma: no cover - placeholder
    """Placeholder for gear bonus lookup."""
    return {}


def _buff_mods(obj) -> Dict[str, int]:  # pragma: no cover - placeholder
    """Placeholder for buff/debuff bonus lookup."""
    return {}


# -------------------------------------------------------------
# Core API
# -------------------------------------------------------------


def refresh_stats(obj) -> None:
    """Recalculate and cache all stats for ``obj``."""

    # ensure baseline traits exist
    stats.apply_stats(obj)

    race_bonus = _race_mods(obj)
    class_bonus = _class_mods(obj)
    gear_bonus = _gear_mods(obj)
    buff_bonus = _buff_mods(obj)

    primary_totals: Dict[str, int] = {}
    for key in PRIMARY_STATS:
        base = obj.traits.get(key).base if obj.traits.get(key) else 0
        total = base
        total += race_bonus.get(key, 0)
        total += class_bonus.get(key, 0)
        total += gear_bonus.get(key, 0)
        total += buff_bonus.get(key, 0)
        if obj.traits.get(key):
            obj.traits.get(key).base = total
        else:
            obj.traits.add(key, key, base=total)
        primary_totals[key] = total

    derived: Dict[str, int] = {}
    for dkey, mapping in STAT_SCALING.items():
        value = 0
        for pkey, weight in mapping.items():
            value += primary_totals.get(pkey, 0) * weight
        derived[dkey] = int(round(value))

    obj.db.derived_stats = derived
    obj.db.primary_stats = primary_totals

    # update resource traits
    if hp := obj.traits.get("health"):
        hp.base = derived.get("HP", hp.base)
        if hp.current > hp.max:
            hp.current = hp.max
    if mp := obj.traits.get("mana"):
        mp.base = derived.get("MP", mp.base)
        if mp.current > mp.max:
            mp.current = mp.max
    if sp := obj.traits.get("stamina"):
        sp.base = derived.get("SP", sp.base)
        if sp.current > sp.max:
            sp.current = sp.max

    # update or add other derived traits
    for key, val in derived.items():
        if key in ("HP", "MP", "SP"):
            continue
        trait = obj.traits.get(key)
        if trait:
            trait.base = val
        else:
            obj.traits.add(key, key, base=val)

    if obj.traits.get("STR"):
        obj.db.carry_capacity = get_effective_stat(obj, "STR") * 20


def get_effective_stat(obj, key: str) -> int:
    """Return ``key`` value including temporary bonuses."""
    base = 0
    if trait := obj.traits.get(key):
        base = trait.value
    base += obj.db.get(f"{key}_bonus", 0)
    base += state_manager.get_temp_bonus(obj, key)
    return int(base)


def get_secondary_stat(obj, key: str) -> int:
    """Return cached secondary stat value."""
    data = obj.db.derived_stats or {}
    return int(data.get(key, 0))


# -------------------------------------------------------------
# Display helpers
# -------------------------------------------------------------
_color_strip_re = re.compile(r"\|.")


def _strip(text: str) -> str:
    return _color_strip_re.sub("", text)


def _pad(text: str, width: int) -> str:
    return text + " " * (width - len(_strip(text)))


def display_stat_block(obj) -> str:
    """Return a formatted stat block for ``obj``."""

    refresh_stats(obj)

    lines = []
    primaries = "  ".join(
        f"{key}: |w{get_effective_stat(obj, key)}|n" for key in PRIMARY_STATS
    )
    lines.append(primaries)

    secondaries = "  ".join(
        f"{key}: |w{get_secondary_stat(obj, key)}|n" for key in SECONDARY_STATS
    )
    lines.append(secondaries)

    width = max(len(_strip(line)) for line in lines)
    top = "╔" + "═" * (width + 2) + "╗"
    bottom = "╚" + "═" * (width + 2) + "╝"
    out = [top]
    for line in lines:
        out.append("║ " + _pad(line, width) + " ║")
    out.append(bottom)
    return "\n".join(out)
