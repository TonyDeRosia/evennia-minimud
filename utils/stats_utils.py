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
from world.system import stat_manager
from utils.currency import from_copper
import math
import re

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


def _strip_colors(text: str) -> str:
    """Remove simple Evennia color codes for width calculations."""
    return re.sub(r"\|.", "", text)


def _pad(text: str, width: int) -> str:
    """Pad ``text`` with spaces to ``width`` accounting for color codes."""
    return text + " " * (width - len(_strip_colors(text)))


def _columns(pairs, cols=3):
    """Return rows of formatted key/value pairs in ``cols`` columns."""
    col_width = max(len(_strip_colors(f"{k}: {v}")) for k, v in pairs) + 2
    lines = []
    for i in range(0, len(pairs), cols):
        row = []
        for k, v in pairs[i : i + cols]:
            entry = f"{k}: |w{v}|n"
            row.append(_pad(entry, col_width))
        lines.append(" ".join(row).rstrip())
    return lines


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
    """Return a formatted character sheet for ``chara``."""

    stat_manager.refresh_stats(chara)

    lines = []

    name = f"|w{chara.key}|n"
    title = _db_get(chara, "title", None)
    if title:
        name += f" - {title}"
    lines.append(name)

    level = _db_get(chara, "level", 1)
    xp = _db_get(chara, "exp", 0)

    hp = chara.traits.get("health")
    mp = chara.traits.get("mana")
    sp = chara.traits.get("stamina")
    if hp and mp and sp:
        hp_line = f"HP |g{int(round(hp.current))}|n/|g{int(round(hp.max))}|n"
        mp_line = f"MP |c{int(round(mp.current))}|n/|c{int(round(mp.max))}|n"
        sp_line = f"SP |w{int(round(sp.current))}|n/|w{int(round(sp.max))}|n"
    else:
        hp_line = mp_line = sp_line = "--/--"

    lines.append(
        f"Lvl {level}  XP {xp}  {hp_line}  {mp_line}  {sp_line}"
    )

    coins = _db_get(chara, "coins", 0)
    if isinstance(coins, int):
        coins = from_copper(coins)
    copper = int(coins.get("copper", 0))
    silver = int(coins.get("silver", 0))
    gold = int(coins.get("gold", 0))
    platinum = int(coins.get("platinum", 0))
    lines.append("COIN POUCH")
    lines.append(
        f"Copper: {copper}  Silver: {silver}  Gold: {gold}  Platinum: {platinum}"
    )

    weight = chara.db.carry_weight or 0
    capacity = chara.db.carry_capacity or 0
    enc = chara.encumbrance_level() if hasattr(chara, "encumbrance_level") else ""
    cw_line = f"Carry Weight: {weight} / {capacity}"
    if enc:
        cw_line += f"  {enc}"
    lines.append(cw_line)

    guild = _db_get(chara, "guild", "")
    if guild:
        lines.append(f"Guild: {guild} ({chara.guild_rank})")
        honor = _db_get(chara, "guild_honor", 0)
        lines.append(f"Honor: {honor}")

    if buffs := chara.tags.get(category="buff", return_list=True):
        lines.append("Buffs: " + iter_to_str(sorted(buffs)))

    lines.append("PRIMARY STATS")
    primaries = "  ".join(
        f"{k}: |w{v}|n" for k, v in get_primary_stats(chara)
    )
    lines.append(primaries)

    lines.append("SECONDARY STATS")
    lines.extend(_columns(get_secondary_stats(chara)))

    width = max(len(_strip_colors(l)) for l in lines)
    top = "+" + "=" * (width + 2) + "+"
    bottom = "+" + "=" * (width + 2) + "+"
    out = [top]
    for line in lines:
        out.append("| " + _pad(line, width) + " |")
    out.append(bottom)
    return "\n".join(out)
