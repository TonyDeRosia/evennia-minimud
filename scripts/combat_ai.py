from random import choice
from typeclasses.scripts import Script

class BaseCombatAI(Script):
    """Base class for simple combat AI behavior."""

    def at_script_creation(self):
        self.interval = 5
        self.persistent = True
        # Optional flag controlling movement when players are in the same room.
        # When ``True`` the NPC will remain in place if ``select_target`` finds a
        # player in the current location.
        self.db.skip_move_if_target = False

    def find_target(self, predicate):
        """Return the first object in the room matching ``predicate``."""
        npc = self.obj
        if not npc or not npc.location:
            return None
        for obj in npc.location.contents:
            if predicate(obj):
                return obj
        return None

    def select_target(self):
        """Return a valid player character in the same room or ``None``."""
        return self.find_target(
            lambda obj: getattr(obj, "account", None)
            and not obj.tags.has("unconscious", category="status")
        )

    def attack_target(self, target):
        npc = self.obj
        if not npc or not target:
            return
        npc.execute_cmd(f"kill {target.key}")

    def _adjacent_exit_to_target(self):
        """Return an exit leading to a room with a viable target, if any."""
        npc = self.obj
        if not npc or not npc.location:
            return None
        for ex in npc.location.exits:
            dest = ex.destination
            if not dest:
                continue
            for obj in dest.contents:
                if getattr(obj, "account", None) and not obj.tags.has(
                    "unconscious", category="status"
                ):
                    return ex
        return None

    def move(self):
        npc = self.obj
        if not npc or not npc.location:
            return
        if self.db.skip_move_if_target and self.select_target():
            return
        exits = npc.location.contents_get(content_type="exit")
        if not exits:
            return

        exit_obj = self._adjacent_exit_to_target()
        if not exit_obj:
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
