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
    """Return current core stat values with equipment bonuses."""

    stats = []
    bonuses = getattr(chara.db, "equip_bonuses", {}) or {}

    for key in CORE_STAT_KEYS:
        trait = chara.traits.get(key)
        total = int(math.ceil(trait.value)) if trait else 0
        bonus = int(bonuses.get(key, 0))
        base = total - bonus
        stats.append((key, base, bonus))

    if (per := chara.traits.get(PRIMARY_EXTRA)):
        total = int(math.ceil(per.value))
        bonus = int(bonuses.get(PRIMARY_EXTRA, 0))
        base = total - bonus
        stats.append(("PER", base, bonus))

    return stats


def get_secondary_stats(chara):
    """Return computed secondary stats with equipment bonuses."""

    stats = []
    bonuses = getattr(chara.db, "equip_bonuses", {}) or {}

    for key in SECONDARY_KEYS:
        total = int(round(sum_bonus(chara, key)))
        bonus = int(bonuses.get(key, 0))
        base = total - bonus
        display = SECONDARY_DISPLAY.get(key, key.replace("_", " ").title())
        stats.append((display, base, bonus))

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
        hp_disp = f"{int(hp.current)}/{int(hp.max)}"
        mp_disp = f"{int(mp.current)}/{int(mp.max)}"
        sp_disp = f"{int(sp.current)}/{int(sp.max)}"
    else:
        hp_disp = mp_disp = sp_disp = "--/--"

    sated_val = 0
    if hasattr(chara.db, "sated"):
        sated_val = chara.db.sated or 0
    elif chara.traits.get("sated"):
        sated_val = chara.traits.sated.value
    if sated_val <= 0:
        sated_disp = "|r0 (URGENT)|n"
    elif sated_val < 5:
        sated_disp = f"|y{sated_val}|n"
    else:
        sated_disp = f"|g{sated_val}|n"

    lines.append(
        f"|YLvl {level}|n  |CXP|n {xp}  |rHP|n {hp_disp}  |cMP|n {mp_disp}  |gSP|n {sp_disp}"
    )
    lines.append(f"|ySated|n {sated_disp}")

    coins = {
        "copper": _db_get(chara, "copper", 0),
        "silver": _db_get(chara, "silver", 0),
        "gold": _db_get(chara, "gold", 0),
        "platinum": _db_get(chara, "platinum", 0),
    }
    copper = int(coins.get("copper", 0))
    silver = int(coins.get("silver", 0))
    gold = int(coins.get("gold", 0))
    platinum = int(coins.get("platinum", 0))
    lines.append("")
    lines.append("|YCOIN POUCH|n")
    lines.append(
        f"Copper: {copper}  Silver: {silver}  Gold: {gold}  Platinum: {platinum}"
    )
    lines.append("")

    weight = chara.db.carry_weight or 0
    capacity = chara.db.carry_capacity or 0
    enc = chara.encumbrance_level() if hasattr(chara, "encumbrance_level") else ""
    cw_line = f"Carry Weight: {weight} / {capacity}"
    if enc:
        cw_line += f"  {enc}"
    lines.append(f"|Y{cw_line}|n")

    guild = _db_get(chara, "guild", "")
    if guild:
        lines.append(f"Guild: {guild} ({chara.guild_rank})")
        gp_map = _db_get(chara, "guild_points", {}) or {}
        points = gp_map.get(guild, 0)
        lines.append(f"Guild Points: {points}")

    if buffs := chara.tags.get(category="buff", return_list=True):
        lines.append("Buffs: " + iter_to_str(sorted(buffs)))

    lines.append("")
    lines.append("|YPRIMARY STATS|n")
    primaries_list = []
    for key, base, bonus in get_primary_stats(chara):
        total = base + bonus
        if bonus:
            primaries_list.append(f"{key}: |w{total}|n (+{bonus})")
        else:
            primaries_list.append(f"{key}: |w{total}|n")
    primaries = "  ".join(primaries_list)
    lines.append(primaries)

    lines.append("")
    lines.append("|YSECONDARY STATS|n")
    secondary_pairs = []
    for name, base, bonus in get_secondary_stats(chara):
        total = base + bonus
        val = f"{total} (+{bonus})" if bonus else f"{total}"
        secondary_pairs.append((name, val))
    lines.extend(_columns(secondary_pairs))

    width = max(len(_strip_colors(l)) for l in lines)
    top = "+" + "=" * (width + 2) + "+"
    bottom = "+" + "=" * (width + 2) + "+"
    out = [top]
    for line in lines:
        out.append("| " + _pad(line, width) + " |")
    out.append(bottom)
    return "\n".join(out)
