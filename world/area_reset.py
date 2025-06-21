from evennia.scripts.scripts import DefaultScript
from world.areas import get_areas, update_area
from utils.script_utils import respawn_area

class AreaReset(DefaultScript):
    """Global script that increments area ages and performs resets."""

    def at_script_creation(self):
        self.key = "area_reset"
        self.desc = "Handles area reset timers"
        self.interval = 60
        self.persistent = True

    def at_repeat(self):
        areas = get_areas()
        for idx, area in enumerate(areas):
            area.age += 1
            if area.reset_interval and area.age >= area.reset_interval:
                area.age = 0
                respawn_area(area.key.lower())
            update_area(idx, area)
