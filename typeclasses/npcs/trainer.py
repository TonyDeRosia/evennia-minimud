from . import BaseNPC
from world.npc_roles import TrainerRole


class TrainerNPC(TrainerRole, BaseNPC):
    """NPC that teaches skills or abilities."""

    pass
