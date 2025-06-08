from . import BaseNPC
from world.npc_roles import EventNPCRole


class EventNPC(EventNPCRole, BaseNPC):
    """NPC tied to special events."""

    pass
