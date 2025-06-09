"""Banker NPC typeclass."""

from . import BaseNPC
from world.npc_roles import BankerRole


class BankerNPC(BankerRole, BaseNPC):
    """NPC that handles currency transactions or storage.

    This subclass exists primarily to tag banker NPCs so game builders can
    easily identify and extend them. Additional banker-specific behavior can be
    added here.
    """

    def at_character_arrive(self, chara, **kwargs):
        """Greet arriving characters with a helpful message."""
        super().at_character_arrive(chara, **kwargs)
        if chara.has_account:
            chara.msg(f"{self.key} says, 'Keep your coins safe with me.'")

