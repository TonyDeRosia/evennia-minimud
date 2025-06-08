from typeclasses.characters import NPC

class BaseNPC(NPC):
    """Base NPC typeclass for specialized behaviors."""

    pass

from .merchant import MerchantNPC  # noqa: E402
from .banker import BankerNPC  # noqa: E402
from .trainer import TrainerNPC  # noqa: E402
from .wanderer import WandererNPC  # noqa: E402
from .guildmaster import GuildmasterNPC  # noqa: E402
from .guild_receptionist import GuildReceptionistNPC  # noqa: E402
from .questgiver import QuestGiverNPC  # noqa: E402
from .combat_trainer import CombatTrainerNPC  # noqa: E402
from .event_npc import EventNPC  # noqa: E402

__all__ = [
    "BaseNPC",
    "MerchantNPC",
    "BankerNPC",
    "TrainerNPC",
    "WandererNPC",
    "GuildmasterNPC",
    "GuildReceptionistNPC",
    "QuestGiverNPC",
    "CombatTrainerNPC",
    "EventNPC",
]
