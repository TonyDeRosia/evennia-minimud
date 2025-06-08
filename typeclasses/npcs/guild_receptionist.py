from . import BaseNPC
from world.npc_roles import GuildReceptionistRole


class GuildReceptionistNPC(GuildReceptionistRole, BaseNPC):
    """NPC that greets visitors for a guild."""

    pass
