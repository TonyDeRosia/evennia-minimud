from . import BaseNPC
from world.npc_roles import QuestGiverRole


class QuestGiverNPC(QuestGiverRole, BaseNPC):
    """NPC that offers quests."""

    pass
