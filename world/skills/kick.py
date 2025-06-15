from combat.combat_actions import CombatResult
from combat.combat_utils import roll_damage, roll_evade
from combat.damage_types import DamageType
from world.system import stat_manager, state_manager
from .skill import Skill


class Kick(Skill):
    """Basic unarmed kick attack."""

    name = "kick"
    cooldown = 4
    stamina_cost = 5
    damage = (1, 4)

    def resolve(self, user, target):
        self.improve(user)
        if not stat_manager.check_hit(user, target):
            return CombatResult(actor=user, target=target, message=f"{user.key}'s kick misses {target.key}.")
        if roll_evade(user, target):
            return CombatResult(actor=user, target=target, message=f"{target.key} evades the kick!")
        dmg = roll_damage(self.damage)
        str_val = state_manager.get_effective_stat(user, "STR")
        dmg = int(dmg + str_val * 0.2)
        return CombatResult(
            actor=user,
            target=target,
            message=f"{user.key} kicks {target.key}!",
            damage=dmg,
            damage_type=DamageType.BLUDGEONING,
        )
