from dataclasses import dataclass
from typing import List, Optional


@dataclass
class Stat:
    key: str
    display: str
    trait_type: str = "counter"
    base: int = 0
    min: int = 0
    max: int = 100
    rate: Optional[float] = None
    stat: Optional[str] = None


# Core character attributes
CORE_STATS: List[Stat] = [
    Stat("STR", "STR", base=5),
    Stat("CON", "CON", base=5),
    Stat("DEX", "DEX", base=5),
    Stat("INT", "INT", base=5),
    Stat("WIS", "WIS", base=5),
    Stat("LUCK", "LUCK", base=5),
]

# Primary resources
RESOURCE_STATS: List[Stat] = [
    Stat("health", "Health", trait_type="gauge", base=100, rate=0.0),
    Stat("mana", "Mana", trait_type="gauge", base=100, rate=0.0),
    Stat("stamina", "Stamina", trait_type="gauge", base=100, rate=0.0),
]

# Base skill for avoiding damage
EVASION_STAT = Stat("evasion", "Evasion", stat="DEX")

# Defense-oriented stats
DEFENSE_STATS: List[Stat] = [
    Stat("armor", "Armor", stat="CON"),
    Stat("magic_resist", "Magic Resist", stat="WIS"),
    Stat("dodge", "Dodge", stat="DEX"),
    Stat("block_rate", "Block Rate", stat="STR"),
    Stat("parry_rate", "Parry Rate", stat="DEX"),
    Stat("status_resist", "Status Resist", stat="CON"),
    Stat("crit_resist", "Critical Resist", stat="CON"),
]
# TODO: implement usage of status_resist and crit_resist in combat rolls

# Offense-oriented stats
OFFENSE_STATS: List[Stat] = [
    Stat("attack_power", "Attack Power", stat="STR"),
    Stat("spell_power", "Spell Power", stat="INT"),
    Stat("crit_chance", "Critical Chance", stat="LUCK"),
    Stat("crit_bonus", "Critical Damage Bonus", stat="STR"),
    Stat("accuracy", "Accuracy", stat="DEX"),
    Stat("piercing", "Armor Penetration", stat="STR"),
    Stat("spell_penetration", "Spell Penetration", stat="INT"),
]

# Regeneration & sustain stats
REGEN_STATS: List[Stat] = [
    Stat("health_regen", "Health Regen", stat="CON"),
    Stat("mana_regen", "Mana Regen", stat="WIS"),
    Stat("stamina_regen", "Stamina Regen", stat="CON"),
    Stat("lifesteal", "Lifesteal", stat="STR"),
    Stat("leech", "Leech", stat="INT"),
]

# Combat timing & tempo stats
TEMPO_STATS: List[Stat] = [
    Stat("cooldown_reduction", "Cooldown Reduction", stat="WIS"),
    Stat("initiative", "Initiative", stat="DEX"),
]

# Utility / miscellaneous stats
UTILITY_STATS: List[Stat] = [
    Stat("stealth", "Stealth", stat="DEX"),
    Stat("detection", "Detection", stat="WIS"),
    Stat("perception", "Perception", base=5, stat="WIS"),
    Stat("threat", "Threat", stat="STR"),
    Stat("movement_speed", "Movement Speed", base=1, stat="DEX"),
    Stat("craft_bonus", "Crafting Bonus", stat="INT"),
]

# PvP / guild-related stats
PVP_STATS: List[Stat] = [
    Stat("pvp_power", "PvP Power", stat="STR"),
    Stat("pvp_resilience", "PvP Resilience", stat="CON"),
    Stat("guild_honor_mod", "Guild Honor Rank Modifiers", stat="WIS"),
]


ALL_STATS: List[Stat] = (
    CORE_STATS
    + RESOURCE_STATS
    + [EVASION_STAT]
    + DEFENSE_STATS
    + OFFENSE_STATS
    + REGEN_STATS
    + TEMPO_STATS
    + UTILITY_STATS
    + PVP_STATS
)

# Convenience: list of only core stat keys
CORE_STAT_KEYS = [stat.key for stat in CORE_STATS]


def apply_stats(chara):
    """Add default stats to a character if missing."""
    for stat in ALL_STATS:
        if chara.traits.get(stat.key):
            continue
        kwargs = {
            "trait_type": stat.trait_type,
            "min": stat.min,
            "max": stat.max,
            "base": stat.base,
        }
        if stat.trait_type == "gauge" and stat.rate is not None:
            kwargs["rate"] = stat.rate
        if stat.stat:
            kwargs["stat"] = stat.stat
        chara.traits.add(stat.key, stat.display, **kwargs)


def sum_bonus(obj, stat_key: str) -> int:
    """Return the total value of a stat, including bonuses."""
    total = 0
    if (trait := obj.traits.get(stat_key)):
        total += trait.value
    # allow bonuses stored directly on the character
    if hasattr(obj, "attributes"):
        total += obj.attributes.get(f"{stat_key}_bonus", default=0)
    else:
        get_bonus = getattr(getattr(obj, "db", None), "get", None)
        if callable(get_bonus):
            try:
                total += get_bonus(f"{stat_key}_bonus", 0)
            except Exception:
                pass
    try:
        from evennia.contrib.game_systems.clothing.clothing import get_worn_clothes

        for item in get_worn_clothes(obj):
            if hasattr(item, "attributes"):
                total += item.attributes.get(f"{stat_key}_bonus", default=0)
            else:
                item_get = getattr(getattr(item, "db", None), "get", None)
                if callable(item_get):
                    try:
                        total += item_get(f"{stat_key}_bonus", 0)
                    except Exception:
                        pass
    except Exception:  # pragma: no cover - clothing contrib may not be loaded
        pass
    return total


from world.system import state_manager


def check_stealth_detection(attacker, target) -> bool:
    """Compare attacker stealth vs target perception."""
    attacker_stealth = state_manager.get_effective_stat(attacker, "stealth")
    target_perception = state_manager.get_effective_stat(target, "perception")
    if target_perception >= attacker_stealth:
        attacker.msg(
            "|rYour stealth attempt fails. The target's perception is too high – they notice you!|n"
        )
        target.msg(
            "|gYou sense movement nearby and spot the incoming attack before it lands!|n"
        )
        attacker.db.is_stealthed = False
        return True
    return False
