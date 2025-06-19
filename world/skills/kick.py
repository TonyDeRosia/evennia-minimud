from combat.combat_actions import CombatResult
from combat.combat_utils import roll_evade
from combat.damage_types import DamageType
from world.system import stat_manager
from .skill import Skill


class Kick(Skill):
    """Basic unarmed kick attack."""

    name = "kick"
    #: Proficiency with this skill is boosted by unarmed training
    support_skill = "unarmed"
    cooldown = 4
    stamina_cost = 5
    base_damage = 5

    def resolve(self, user, target):
        """Resolve the kick immediately, returning the damage dealt."""

        self.improve(user)

        if not stat_manager.check_hit(user, target) or roll_evade(user, target):
            return CombatResult(
                actor=user,
                target=target,
                message=f"{user.key}'s kick misses {target.key}.",
            )

        str_val = stat_manager.get_effective_stat(user, "STR")
        dmg = int(self.base_damage + str_val * 0.2)

        return CombatResult(
            actor=user,
            target=target,
            message=f"$You() kick(s) {target.key} for {dmg} damage!",
            damage=dmg,
            damage_type=DamageType.BLUDGEONING,
        )
