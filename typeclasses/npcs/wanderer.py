from . import BaseNPC


class WandererNPC(BaseNPC):
    """NPC that roams locations randomly."""

    def at_object_creation(self):
        """Default to using the ``wander`` AI type."""
        super().at_object_creation()
        if not self.db.ai_type:
            self.db.ai_type = "wander"
        if not self.scripts.get("npc_ai"):
            from scripts.npc_ai_script import NPCAIScript

            self.scripts.add(NPCAIScript, key="npc_ai")
