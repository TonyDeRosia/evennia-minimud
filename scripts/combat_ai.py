from random import choice
from typeclasses.scripts import Script

class BaseCombatAI(Script):
    """Base class for simple combat AI behavior."""

    def at_script_creation(self):
        self.interval = 5
        self.persistent = True

    def select_target(self):
        """Return a valid player character in the same room or ``None``."""
        npc = self.obj
        if not npc or not npc.location:
            return None
        for obj in npc.location.contents:
            if getattr(obj, "account", None) and not obj.tags.has("unconscious", category="status"):
                return obj
        return None

    def attack_target(self, target):
        npc = self.obj
        if not npc or not target:
            return
        npc.execute_cmd(f"kill {target.key}")

    def move(self):
        npc = self.obj
        if not npc or not npc.location:
            return
        exits = npc.location.contents_get(content_type="exit")
        if exits:
            exit_obj = choice(exits)
            exit_obj.at_traverse(npc, exit_obj.destination)

    def at_repeat(self):
        npc = self.obj
        if not npc or not npc.location or npc.in_combat:
            return
        target = self.select_target()
        if target:
            self.attack_target(target)
        else:
            self.move()
