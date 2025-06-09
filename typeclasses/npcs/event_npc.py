"""Event NPC typeclass."""

from . import BaseNPC
from world.npc_roles import EventNPCRole


class EventNPC(EventNPCRole, BaseNPC):
    """NPC tied to special events.

    Minimal for now; serves as a tag for NPCs that can start or
    participate in time-limited events.
    """

    def at_character_arrive(self, chara, **kwargs):
        """Hint to the player that an event is available."""
        super().at_character_arrive(chara, **kwargs)
        if chara.has_account:
            chara.msg(f"{self.key} says, 'Something exciting is about to happen!'")

