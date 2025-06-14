from .combat_ai import BaseCombatAI

class BanditAI(BaseCombatAI):
    """Roams around and attacks weaker players."""

    def at_script_creation(self):
        super().at_script_creation()
        self.key = "bandit_ai"
        self.desc = "Bandit combat behavior"

    def select_target(self):
        npc = self.obj
        if not npc or not npc.location:
            return None
        for obj in npc.location.contents:
            if obj.has_account and obj.db.level and npc.db.level:
                if obj.db.level < npc.db.level:
                    return obj
        return None
