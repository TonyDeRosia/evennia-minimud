from evennia.scripts.scripts import DefaultScript
from world.areas import get_areas, update_area
from evennia.scripts.models import ScriptDB

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
                script = ScriptDB.objects.filter(db_key="spawn_manager").first()
                if script and hasattr(script, "force_respawn"):
                    for entry in script.db.entries:
                        if entry.get("area") == area.key.lower():
                            rid = entry.get("room_id")
                            if rid is None:
                                rid = entry.get("room")
                                if isinstance(rid, str) and rid.isdigit():
                                    rid = int(rid)
                            script.force_respawn(rid)
            update_area(idx, area)
