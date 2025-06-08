from . import BaseNPC
from world.npc_roles import GuildmasterRole


class GuildmasterNPC(GuildmasterRole, BaseNPC):
    """NPC that oversees guild management."""

    pass
