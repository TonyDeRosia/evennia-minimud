"""Guild definitions and utilities."""

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
    guild = GUILDS.get(guild_name)
    if not guild:
        return ""
    title = guild["ranks"][0][1]
    for threshold, rank in guild["ranks"]:
        if honor >= threshold:
            title = rank
        else:
            break
    return title
