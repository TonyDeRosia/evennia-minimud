"""Merchant NPC typeclass."""

from . import BaseNPC
from world.npc_roles import MerchantRole


class MerchantNPC(MerchantRole, BaseNPC):
    """NPC that buys and sells items.

    The class is intentionally minimal and mainly serves as a convenient
    tag for merchant NPCs. Extend this typeclass if your game requires more
    complex shopkeeper behavior.
    """

    arrival_message = "Take a look at my wares!"

