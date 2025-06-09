from random import choice
from typeclasses.scripts import Script

class GuardPatrol(Script):
    """Walk a patrol path and attack wanted players."""

    def at_script_creation(self):
        self.key = "guard_patrol"
        self.desc = "Guard patrol behavior"
        self.interval = 10
        self.persistent = True
        self.db.patrol = []
        self.db.index = 0

    def at_repeat(self):
        npc = self.obj
        if not npc or not npc.location:
            return
        for obj in npc.location.contents:
            if obj.tags.get("wanted"):
                npc.execute_cmd(f"kill {obj.key}")
                return
        path = self.db.patrol
        if path:
            exit_name = path[self.db.index % len(path)]
            self.db.index = (self.db.index + 1) % len(path)
            exit_obj = npc.search(exit_name, location=npc.location)
            if exit_obj:
                exit_obj.at_traverse(npc, exit_obj.destination)
        else:
            exits = npc.location.contents_get(content_type="exit")
            if exits:
                choice(exits).at_traverse(npc, exits[0].destination)
