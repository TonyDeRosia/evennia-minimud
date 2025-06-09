"""Guild receptionist NPC typeclass."""

from . import BaseNPC
from world.npc_roles import GuildReceptionistRole


class GuildReceptionistNPC(GuildReceptionistRole, BaseNPC):
    """NPC that greets visitors for a guild.

    This subclass mainly attaches the :class:`~world.npc_roles.GuildReceptionistRole`
    mixin so that it can be referenced and extended later.
    """

    def at_character_arrive(self, chara, **kwargs):
        """Welcome arriving visitors."""
        super().at_character_arrive(chara, **kwargs)
        if chara.has_account:
            self.greet_visitor(chara)

