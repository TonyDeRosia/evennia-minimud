from typeclasses.scripts import Script


class SatedDecayScript(Script):
    """Periodically reduce character sated values."""

    def at_script_creation(self):
        self.key = "sated_decay"
        self.desc = "Reduce character sated values over time"
        self.interval = 60
        self.persistent = True

    def at_repeat(self):
        from typeclasses.characters import Character

        thresholds = {50: "You feel a bit peckish.",
                      20: "You are getting hungry.",
                      1: "You are starving!"}

        for char in Character.objects.all():
            sated = getattr(char.db, "sated", None)
            if sated is None or sated <= 0:
                continue
            old = sated
            char.db.sated = max(sated - 1, 0)
            new_val = char.db.sated
            for threshold, msg in thresholds.items():
                if old >= threshold > new_val:
                    if hasattr(char, "msg"):
                        char.msg(msg)
                    break


