"""Trainer NPC typeclass."""

from . import BaseNPC
from world.npc_roles import TrainerRole


class TrainerNPC(TrainerRole, BaseNPC):
    """NPC that teaches skills or abilities.

    This subclass is provided mainly for tagging purposes so that new trainer
    behavior can be implemented without altering the core NPC class.
    """

    def at_character_arrive(self, chara, **kwargs):
        """Offer training when a player enters."""
        super().at_character_arrive(chara, **kwargs)
        if chara.has_account:
            chara.msg(f"{self.key} says, 'Interested in honing your skills?'")

