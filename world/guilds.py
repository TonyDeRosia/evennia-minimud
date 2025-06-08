"""Guild definitions and utilities."""

from dataclasses import dataclass, asdict, field
from typing import Dict, List, Optional, Tuple

from evennia.server.models import ServerConfig

ADVENTURERS_GUILD_RANKS = [
    (0, "Private"),
    (10, "Corporal"),
    (20, "Sergeant"),
    (30, "Senior Sergeant"),
    (45, "Lieutenant"),
    (60, "Captain"),
    (80, "Major"),
    (100, "Colonel"),
    (125, "Field Marshal"),
    (150, "Grand Marshal"),
]


@dataclass
class Guild:
    """Simple data container for a guild."""

    name: str
    desc: str = ""
    home: Optional[int] = None
    ranks: List[Tuple[int, str]] = field(default_factory=list)
    members: Dict[str, int] = field(default_factory=dict)
    rank_thresholds: Dict[str, int] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict) -> "Guild":
        return cls(
            name=data.get("name", ""),
            desc=data.get("desc", ""),
            home=data.get("home"),
            ranks=data.get("ranks", []),
            members=data.get("members", {}),
            rank_thresholds=data.get("rank_thresholds", {}),
        )

    def to_dict(self) -> Dict:
        return asdict(self)


_REGISTRY_KEY = "guild_registry"


def _load_registry() -> List[Dict]:
    return ServerConfig.objects.conf(_REGISTRY_KEY, default=list)


def _save_registry(registry: List[Dict]):
    ServerConfig.objects.conf(_REGISTRY_KEY, value=registry)


def get_guilds() -> List[Guild]:
    """Return all stored guilds."""
    data = _load_registry()
    guilds = [Guild.from_dict(d) for d in data]
    if not guilds:
        # seed with default Adventurers Guild if none exist
        default = Guild(
            name="Adventurers Guild",
            desc="The guild of brave adventurers.",
            ranks=ADVENTURERS_GUILD_RANKS,
            rank_thresholds={title: lvl for lvl, title in ADVENTURERS_GUILD_RANKS},
        )
        guilds.append(default)
        _save_registry([g.to_dict() for g in guilds])
    return guilds


def save_guild(guild: Guild):
    """Add a new guild to the registry."""
    registry = _load_registry()
    registry.append(guild.to_dict())
    _save_registry(registry)


def update_guild(index: int, guild: Guild):
    """Update guild at index."""
    registry = _load_registry()
    registry[index] = guild.to_dict()
    _save_registry(registry)


def find_guild(name: str) -> Tuple[int, Optional[Guild]]:
    """Return index and guild matching name (case-insensitive)."""
    registry = _load_registry()
    for i, data in enumerate(registry):
        guild = Guild.from_dict(data)
        if guild.name.lower() == name.lower():
            return i, guild
    return -1, None

GUILDS = {
    "Adventurers Guild": {
        "crest": "|b[|gAdventurers Guild|b]|n",
        "honor_name": "Guild Honor",
        "motd": "Seek glory and fortune!",
        "ranks": ADVENTURERS_GUILD_RANKS,
    }
}


def get_rank_title(guild_name: str, honor: int) -> str:
    """Return the rank title for a guild member."""
    guild_map = {g.name: g for g in get_guilds()}
    guild = guild_map.get(guild_name)
    ranks = []
    if guild:
        ranks = guild.ranks
    else:
        # fallback to legacy dictionary
        info = GUILDS.get(guild_name)
        if info:
            ranks = info.get("ranks", [])
    if not ranks:
        return ""
    title = ranks[0][1]
    for threshold, rank in ranks:
        if honor >= threshold:
            title = rank
        else:
            break
    return title


def auto_promote(player, guild: Guild):
    """Update player's guild rank based on their points in the guild."""
    if not guild.rank_thresholds:
        return
    gp_map = player.db.guild_points or {}
    points = gp_map.get(guild.name, 0)
    new_rank = ""
    for title, threshold in sorted(guild.rank_thresholds.items(), key=lambda it: it[1]):
        if points >= threshold:
            new_rank = title
        else:
            break
    if player.db.guild_rank != new_rank:
        player.db.guild_rank = new_rank
