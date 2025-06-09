"""Combat trainer NPC typeclass."""

from . import BaseNPC
from world.npc_roles import CombatTrainerRole


class CombatTrainerNPC(CombatTrainerRole, BaseNPC):
    """NPC that trains players in combat.

    Kept intentionally small so specialized combat training logic can be
    added when needed.
    """

    def at_character_arrive(self, chara, **kwargs):
        """Encourage the player to spar."""
        super().at_character_arrive(chara, **kwargs)
        if chara.has_account:
            chara.msg(f"{self.key} says, 'Ready to test your mettle?'")

