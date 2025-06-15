from random import random


class Skill:
    """Base skill providing proficiency tracking."""

    name = "skill"
    cooldown = 0
    stamina_cost = 0

    def improve(self, user) -> None:
        """Increase proficiency by 1% every 25 uses and randomly."""
        uses = user.db.skill_uses or {}
        count = uses.get(self.name, 0) + 1
        uses[self.name] = count
        user.db.skill_uses = uses
        profs = user.db.proficiencies or {}
        prof = profs.get(self.name, 0)

        improved = False
        if prof < 100 and random() <= 0.15:
            prof += 1
            improved = True

        if count % 25 == 0 and prof < 100:
            prof += 1
            improved = True

        if improved:
            profs[self.name] = min(100, prof)
            user.db.proficiencies = profs

    def resolve(self, user, target):
        """Override in subclasses to produce a CombatResult."""
        raise NotImplementedError
