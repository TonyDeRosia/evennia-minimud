"""Quest giver NPC typeclass."""

from . import BaseNPC
from world.npc_roles import QuestGiverRole


class QuestGiverNPC(QuestGiverRole, BaseNPC):
    """NPC that offers quests to players.

    This class exists mostly so quest-giving NPCs can be easily searched for
    and customized in the future.
    """

    arrival_message = "Ask me for a quest if you're looking for work."

