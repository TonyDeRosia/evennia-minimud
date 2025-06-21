"""Combat trainer NPC typeclass."""

from . import BaseNPC
from world.npc_roles import CombatTrainerRole


class CombatTrainerNPC(CombatTrainerRole, BaseNPC):
    """NPC that trains players in combat.

    Kept intentionally small so specialized combat training logic can be
    added when needed.
    """

    arrival_message = "Ready to test your mettle?"

