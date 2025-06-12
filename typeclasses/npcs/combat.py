"""Combat-ready NPC typeclass."""

from . import BaseNPC


class CombatNPC(BaseNPC):
    """NPC that can engage in combat by default."""

    def at_object_creation(self):
        super().at_object_creation()
        self.db.can_attack = True

