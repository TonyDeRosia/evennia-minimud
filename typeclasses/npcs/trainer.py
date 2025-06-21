"""Trainer NPC typeclass."""

from . import BaseNPC
from world.npc_roles import TrainerRole


class TrainerNPC(TrainerRole, BaseNPC):
    """NPC that teaches skills or abilities.

    This subclass is provided mainly for tagging purposes so that new trainer
    behavior can be implemented without altering the core NPC class.
    """

    arrival_message = "Interested in honing your skills?"

