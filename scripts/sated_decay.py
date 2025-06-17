from typeclasses.scripts import Script
from world.system import state_manager


class SatedDecayScript(Script):
    """Periodically reduce character sated values."""

    def at_script_creation(self):
        self.key = "sated_decay"
        self.desc = "Reduce character sated values over time"
        self.interval = 60
        self.persistent = True

    def at_repeat(self):
        from typeclasses.characters import Character

        for char in Character.objects.all():
            state_manager.tick_character(char)
