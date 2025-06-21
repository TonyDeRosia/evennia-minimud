"""Guildmaster NPC typeclass."""

from . import BaseNPC
from world.npc_roles import GuildmasterRole


class GuildmasterNPC(GuildmasterRole, BaseNPC):
    """NPC that oversees guild management.

    Primarily exists for role tagging so builders can easily customize
    guildmaster behaviors without modifying the base NPC class.
    """

    arrival_message = "Step forward if you seek guild business."

