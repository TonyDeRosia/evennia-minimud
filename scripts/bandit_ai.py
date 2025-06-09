from random import choice
from typeclasses.scripts import Script

class BanditAI(Script):
    """Roams around and attacks weaker players."""

    def at_script_creation(self):
        self.key = "bandit_ai"
        self.desc = "Bandit combat behavior"
        self.interval = 5
        self.persistent = True

    def at_repeat(self):
        npc = self.obj
        if not npc or not npc.location:
            return
        if npc.in_combat:
            return
        # look for an easy target
        for obj in npc.location.contents:
            if obj.has_account and obj.db.level and npc.db.level:
                if obj.db.level < npc.db.level:
                    npc.execute_cmd(f"kill {obj.key}")
                    return
        # wander if no target
        exits = npc.location.contents_get(content_type="exit")
        if exits:
            exit_obj = choice(exits)
            exit_obj.at_traverse(npc, exit_obj.destination)
