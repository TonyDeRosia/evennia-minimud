from . import BaseNPC
from world.npc_roles import MerchantRole


class MerchantNPC(MerchantRole, BaseNPC):
    """NPC that buys and sells items."""

    pass
