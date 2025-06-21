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
        return self.find_target(
            lambda obj: obj.has_account
            and obj.db.level
            and npc.db.level
            and obj.db.level < npc.db.level
        )
