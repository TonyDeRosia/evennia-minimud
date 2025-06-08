"""Script that drives NPC AI behavior."""

from typeclasses.scripts import Script
from world.npc_handlers.ai import process_ai


class NPCAIScript(Script):
    """Periodically call :func:`process_ai` for the attached NPC."""

    def at_script_creation(self):
        self.interval = 10
        self.persistent = True

    def at_repeat(self):
        if self.obj:
            process_ai(self.obj)
