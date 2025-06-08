from . import BaseNPC
from world.npc_roles import BankerRole


class BankerNPC(BankerRole, BaseNPC):
    """NPC that handles currency transactions or storage."""

    pass
