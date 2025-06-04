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
    Stat("health", "Health", trait_type="gauge", base=100, rate=0.1),
    Stat("mana", "Mana", trait_type="gauge", base=100, rate=0.1),
    Stat("stamina", "Stamina", trait_type="gauge", base=100, rate=0.1),
]

# Base skill for avoiding damage
EVASION_STAT = Stat("evasion", "Evasion", stat="DEX")

# Defense-oriented stats
DEFENSE_STATS: List[Stat] = [
    Stat("armor", "Armor"),
    Stat("magic_resist", "Magic Resist"),
    Stat("dodge", "Dodge"),
    Stat("block_rate", "Block Rate"),
    Stat("parry_rate", "Parry Rate"),
    Stat("status_resist", "Status Resist"),
    Stat("crit_resist", "Critical Resist"),
]

# Offense-oriented stats
OFFENSE_STATS: List[Stat] = [
    Stat("attack_power", "Attack Power"),
    Stat("spell_power", "Spell Power"),
    Stat("crit_chance", "Critical Chance"),
    Stat("crit_bonus", "Critical Damage Bonus"),
    Stat("accuracy", "Accuracy"),
    Stat("piercing", "Armor Penetration"),
    Stat("spell_penetration", "Spell Penetration"),
]

# Regeneration & sustain stats
REGEN_STATS: List[Stat] = [
    Stat("health_regen", "Health Regen"),
    Stat("mana_regen", "Mana Regen"),
    Stat("stamina_regen", "Stamina Regen"),
    Stat("lifesteal", "Lifesteal"),
    Stat("leech", "Leech"),
]

# Combat timing & tempo stats
TEMPO_STATS: List[Stat] = [
    Stat("cooldown_reduction", "Cooldown Reduction"),
    Stat("initiative", "Initiative"),
    Stat("gcd_speed", "Global Cooldown Speed"),
]

# Utility / miscellaneous stats
UTILITY_STATS: List[Stat] = [
    Stat("stealth", "Stealth"),
    Stat("detection", "Detection"),
    Stat("threat", "Threat"),
    Stat("movement_speed", "Movement Speed", base=1),
    Stat("craft_bonus", "Crafting Bonus"),
]

# PvP / guild-related stats
PVP_STATS: List[Stat] = [
    Stat("pvp_power", "PvP Power"),
    Stat("pvp_resilience", "PvP Resilience"),
    Stat("guild_honor_mod", "Guild Honor Rank Modifiers"),
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
