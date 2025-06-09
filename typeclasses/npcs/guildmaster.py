"""Guildmaster NPC typeclass."""

from . import BaseNPC
from world.npc_roles import GuildmasterRole


class GuildmasterNPC(GuildmasterRole, BaseNPC):
    """NPC that oversees guild management.

    Primarily exists for role tagging so builders can easily customize
    guildmaster behaviors without modifying the base NPC class.
    """

    def at_character_arrive(self, chara, **kwargs):
        """Offer assistance with guild matters."""
        super().at_character_arrive(chara, **kwargs)
        if chara.has_account:
            chara.msg(f"{self.key} says, 'Step forward if you seek guild business.'")

