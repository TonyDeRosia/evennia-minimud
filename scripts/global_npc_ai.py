"""Global script processing AI for all NPCs each tick."""

from evennia.utils import logger
from typeclasses.scripts import Script
from world.npc_handlers.mob_ai import process_mob_ai
from typeclasses.npcs import BaseNPC


class GlobalNPCAI(Script):
    """Iterate over all NPCs and run their AI once per tick."""

    def at_script_creation(self):
        self.key = "global_npc_ai"
        self.desc = "Global NPC AI processor"
        self.interval = 1
        self.persistent = True

    def at_repeat(self):
        for npc in BaseNPC.objects.all():
            if not (npc.db.ai_type or npc.db.actflags):
                continue
            try:
                process_mob_ai(npc)
            except Exception as err:  # pragma: no cover - log errors
                logger.log_err(f"GlobalNPCAI error on {npc}: {err}")
