from .skill import Skill

class Unarmed(Skill):
    """Passive bonus for fighting without weapons."""

    name = "Unarmed"
    hit_scale = 0.25  # percent per proficiency point
    dmg_scale = 0.5

    def hit_bonus(self, user) -> float:
        prof = (user.db.proficiencies or {}).get(self.name, 0)
        return prof * self.hit_scale

    def damage_bonus(self, user) -> float:
        prof = (user.db.proficiencies or {}).get(self.name, 0)
        return prof * self.dmg_scale
