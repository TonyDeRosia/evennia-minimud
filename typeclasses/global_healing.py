"""Regeneration handler subscribed to the global tick signal."""

from evennia.scripts.scripts import DefaultScript
from evennia.utils.search import search_tag
from typeclasses.global_tick import TICK
from world.system import state_manager

# ---------------------------------------------------------------------------
# This script listens for the :data:`TICK` signal defined in ``global_tick``.
# Whenever the signal is fired, it applies passive regeneration to all
# characters tagged ``tickable``.  Other modules may subscribe to the same
# signal to perform additional per-minute processing.
# ---------------------------------------------------------------------------

class GlobalHealing(DefaultScript):
    """Apply regeneration to tickable characters each time ``TICK`` fires."""

    def at_script_creation(self):
        self.persistent = True

    def at_start(self):
        TICK.connect(self.on_tick)

    def at_stop(self):
        TICK.disconnect(self.on_tick)

    def on_tick(self, sender, **kwargs):
        tickables = search_tag(key="tickable")
        for obj in tickables:
            state_manager.tick_character(obj)
            if obj.tags.has("unconscious", category="status"):
                continue
            state_manager.apply_regen(obj)
            if obj.sessions.count():
                obj.refresh_prompt()

