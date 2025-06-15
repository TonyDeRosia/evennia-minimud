from world.abilities.base import Ability
from world.system import stat_manager


class Kick(Ability):
    """Basic melee kick attack scaling with Strength."""

    name = "kick"
    cooldown = 3
    description = "Kick the enemy with force. Scales with Strength."
    class_type = "skill"

    def apply(self, user, target, proficiency):
        """Apply the kick to ``target``."""
        if not stat_manager.check_hit(user, target):
            return f"{user.key} misses {target.key}."
        base_damage = 5
        str_val = stat_manager.get_effective_stat(user, "STR")
        str_bonus = int(str_val * 0.2)
        damage = base_damage + str_bonus
        damage = int(damage * (1 + (proficiency or 0) / 100))
        target.hp = max(target.hp - damage, 0)
        return f"{user.key} kicks {target.key} for {damage} damage!"
