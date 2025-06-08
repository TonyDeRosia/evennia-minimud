from . import BaseNPC
from world.npc_roles import CombatTrainerRole


class CombatTrainerNPC(CombatTrainerRole, BaseNPC):
    """NPC that trains players in combat."""

    pass
