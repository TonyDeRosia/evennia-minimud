"""Merchant NPC typeclass."""

from . import BaseNPC
from world.npc_roles import MerchantRole


class MerchantNPC(MerchantRole, BaseNPC):
    """NPC that buys and sells items.

    The class is intentionally minimal and mainly serves as a convenient
    tag for merchant NPCs. Extend this typeclass if your game requires more
    complex shopkeeper behavior.
    """

    def at_character_arrive(self, chara, **kwargs):
        """Invite players to browse the wares when they arrive."""
        super().at_character_arrive(chara, **kwargs)
        if chara.has_account:
            chara.msg(f"{self.key} says, 'Take a look at my wares!'")

