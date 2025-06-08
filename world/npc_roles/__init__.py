"""Mixin classes for specialized NPC behaviors."""

from .merchant import MerchantRole
from .banker import BankerRole
from .trainer import TrainerRole
from .guildmaster import GuildmasterRole
from .guild_receptionist import GuildReceptionistRole
from .questgiver import QuestGiverRole
from .combat_trainer import CombatTrainerRole
from .event_npc import EventNPCRole

__all__ = [
    "MerchantRole",
    "BankerRole",
    "TrainerRole",
    "GuildmasterRole",
    "GuildReceptionistRole",
    "QuestGiverRole",
    "CombatTrainerRole",
    "EventNPCRole",
]
