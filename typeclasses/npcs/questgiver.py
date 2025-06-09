"""Quest giver NPC typeclass."""

from . import BaseNPC
from world.npc_roles import QuestGiverRole


class QuestGiverNPC(QuestGiverRole, BaseNPC):
    """NPC that offers quests to players.

    This class exists mostly so quest-giving NPCs can be easily searched for
    and customized in the future.
    """

    def at_character_arrive(self, chara, **kwargs):
        """Remind players they can ask for quests."""
        super().at_character_arrive(chara, **kwargs)
        if chara.has_account:
            chara.msg(f"{self.key} says, 'Ask me for a quest if you're looking for work.'")

