from evennia.utils.evtable import EvTable
from evennia.utils import iter_to_str
from world.stats import (
    CORE_STAT_KEYS,
    EVASION_STAT,
    DEFENSE_STATS,
    OFFENSE_STATS,
    REGEN_STATS,
    TEMPO_STATS,
    UTILITY_STATS,
    PVP_STATS,
    sum_bonus,
    apply_stats,
)
from utils.currency import from_copper
import math

PRIMARY_EXTRA = "perception"

# Build list of secondary stats from world.stats excluding core attributes,
# resources and the perception stat which is displayed with the primaries.
SECONDARY_STATS = (
    [EVASION_STAT]
    + DEFENSE_STATS
    + OFFENSE_STATS
    + REGEN_STATS
    + TEMPO_STATS
    + [stat for stat in UTILITY_STATS if stat.key != PRIMARY_EXTRA]
    + PVP_STATS
)

SECONDARY_KEYS = [stat.key for stat in SECONDARY_STATS]
SECONDARY_DISPLAY = {stat.key: stat.display for stat in SECONDARY_STATS}


def get_primary_stats(chara):
    """Return current core stat values."""
    stats = []
    for key in CORE_STAT_KEYS:
        trait = chara.traits.get(key)
        val = trait.value if trait else 0
        val = int(math.ceil(val))
        stats.append((key, val))
    if (per := chara.traits.get(PRIMARY_EXTRA)):
        stats.append(("PER", int(math.ceil(per.value))))
    return stats


def get_secondary_stats(chara):
    """Return computed secondary stats."""
    stats = []
    for key in SECONDARY_KEYS:
        value = int(round(sum_bonus(chara, key)))
        display = SECONDARY_DISPLAY.get(key, key.replace("_", " ").title())
        stats.append((display, value))
    return stats


def _table_from_pairs(pairs):
    table = EvTable(border="none")
    for key, val in pairs:
        table.add_row(key, val)
    return str(table)


def _db_get(obj, key, default=None):
    """Safely get an AttributeHandler value."""
    db = getattr(obj, "db", None)
    if hasattr(db, "get"):
        try:
            return db.get(key, default)
        except Exception:
            pass
    if hasattr(obj, "attributes"):
        return obj.attributes.get(key, default=default)
    return default


def get_display_scroll(chara):
    """Return a parchment-style stats display for ``chara``."""

    apply_stats(chara)

    lines = []
    name_line = f"|w{chara.key}|n"
    title = _db_get(chara, "title", None)
    if title:
        name_line += f" - {title}"
    lines.append(name_line)

    level = _db_get(chara, "level", 1)
    xp = _db_get(chara, "exp", 0)
    lines.append(f"Level: {level}    XP: {xp}")

    hp = chara.traits.get("health")
    mp = chara.traits.get("mana")
    sp = chara.traits.get("stamina")
    if hp and mp and sp:
        lines.append(
            "Health {} / {}  Mana {} / {}  Stamina {} / {}".format(
                int(round(hp.current)),
                int(round(hp.max)),
                int(round(mp.current)),
                int(round(mp.max)),
                int(round(sp.current)),
                int(round(sp.max)),
            )
        )
    else:
        lines.append("Health --/--  Mana --/--  Stamina --/--")

    coins = _db_get(chara, "coins", 0)
    if isinstance(coins, int):
        coins = from_copper(coins)
    for coin in ["copper", "silver", "gold", "platinum"]:
        amount = int(coins.get(coin, 0))
        lines.append(f"{coin.capitalize()}: {amount}")

    guild = _db_get(chara, "guild", "")
    if guild:
        lines.append(f"Guild: {guild} ({chara.guild_rank})")
        honor = _db_get(chara, "guild_honor", 0)
        lines.append(f"Honor: {honor}")

    if buffs := chara.tags.get(category="buff", return_list=True):
        lines.append("Buffs: " + iter_to_str(sorted(buffs)))

    lines.append("PRIMARY STATS")
    lines.append(_table_from_pairs(get_primary_stats(chara)))

    lines.append("SECONDARY STATS")
    lines.append(_table_from_pairs(get_secondary_stats(chara)))

    return "\n".join(lines)
