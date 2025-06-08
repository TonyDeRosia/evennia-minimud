from evennia.scripts.scripts import DefaultScript

class GlobalTick(DefaultScript):
    """Standalone global ticker that refreshes prompts every minute."""

    def at_script_creation(self):
        self.interval = 60
        self.persistent = True

    def at_repeat(self):
        from evennia.utils.search import search_tag
        from world.system import state_manager

        tickables = search_tag(key="tickable")
        for obj in tickables:
            if hasattr(obj, "at_tick"):
                obj.at_tick()
            else:
                state_manager.tick_character(obj)
