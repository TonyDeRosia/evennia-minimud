"""Banker NPC typeclass."""

from . import BaseNPC
from world.npc_roles import BankerRole


class BankerNPC(BankerRole, BaseNPC):
    """NPC that handles currency transactions or storage.

    This subclass exists primarily to tag banker NPCs so game builders can
    easily identify and extend them. Additional banker-specific behavior can be
    added here.
    """

    arrival_message = "Keep your coins safe with me."

