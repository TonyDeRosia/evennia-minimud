"""Wandering NPC typeclass."""

from . import BaseNPC


class WandererNPC(BaseNPC):
    """NPC that roams locations randomly."""

    def at_object_creation(self):
        """Default to using the ``wander`` AI type."""
        super().at_object_creation()
        if not self.db.ai_type:
            self.db.ai_type = "wander"
        self.tags.add("npc_ai")
