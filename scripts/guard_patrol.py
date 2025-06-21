from .combat_ai import BaseCombatAI

class GuardPatrol(BaseCombatAI):
    """Walk a patrol path and attack wanted players."""

    def at_script_creation(self):
        super().at_script_creation()
        self.key = "guard_patrol"
        self.desc = "Guard patrol behavior"
        self.interval = 10
        self.db.patrol = []
        self.db.index = 0

    def select_target(self):
        npc = self.obj
        if not npc or not npc.location:
            return None
        return self.find_target(lambda obj: obj.tags.get("wanted"))

    def move(self):
        npc = self.obj
        if not npc or not npc.location:
            return
        path = self.db.patrol
        if path:
            exit_name = path[self.db.index % len(path)]
            self.db.index = (self.db.index + 1) % len(path)
            exit_obj = npc.search(exit_name, location=npc.location)
            if exit_obj:
                exit_obj.at_traverse(npc, exit_obj.destination)
                return
        super().move()
