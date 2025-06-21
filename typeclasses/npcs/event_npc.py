"""Event NPC typeclass."""

from . import BaseNPC
from world.npc_roles import EventNPCRole


class EventNPC(EventNPCRole, BaseNPC):
    """NPC tied to special events.

    Minimal for now; serves as a tag for NPCs that can start or
    participate in time-limited events.
    """

    arrival_message = "Something exciting is about to happen!"

