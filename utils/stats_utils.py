from evennia.utils.evtable import EvTable
from evennia.utils import iter_to_str
from world.stats import CORE_STAT_KEYS, sum_bonus


PRIMARY_EXTRA = "perception"
SECONDARY_KEYS = [
    "armor",
    "evasion",
    "block_rate",
    "accuracy",
]


def get_primary_stats(chara):
    """Return current core stat values."""
    stats = []
    for key in CORE_STAT_KEYS:
        trait = chara.traits.get(key)
        val = trait.value if trait else 0
        stats.append((key, val))
    if (per := chara.traits.get(PRIMARY_EXTRA)):
        stats.append(("PER", per.value))
    return stats


def get_secondary_stats(chara):
    """Return computed secondary stats."""
    stats = []
    for key in SECONDARY_KEYS:
        value = sum_bonus(chara, key)
        display = key.replace("_", " ").title()
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
    """Return a parchment-style stats display for chara."""
    lines = []
    name_line = f"|w{chara.key}|n"
    title = _db_get(chara, "title", None)
    if title:
        name_line += f" - {title}"
    lines.append(name_line)

    level = _db_get(chara, "level", 1)
    xp = _db_get(chara, "exp", 0)
    lines.append(f"Level: {level}    XP: {xp}")

    hp = chara.traits.health
    mp = chara.traits.mana
    sp = chara.traits.stamina
    lines.append(
        f"Health {hp.current}/{hp.max}  Mana {mp.current}/{mp.max}  Stamina {sp.current}/{sp.max}"
    )

    coins = _db_get(chara, "coins", 0)
    lines.append(f"Coins: {coins}")

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
