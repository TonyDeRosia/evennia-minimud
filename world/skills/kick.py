from combat.combat_actions import CombatResult
from combat.combat_utils import roll_evade
from combat.damage_types import DamageType
from world.system import stat_manager
from .skill import Skill


class Kick(Skill):
    """Basic unarmed kick attack."""

    name = "kick"
    cooldown = 4
    stamina_cost = 5
    base_damage = 5

    def resolve(self, user, target):
        """Resolve the kick immediately, applying damage to ``target``."""

        self.improve(user)

        profs = user.db.proficiencies or {}
        prof = profs.get(self.name, 0)
        dex = stat_manager.get_effective_stat(user, "DEX")
        chance = stat_manager.proficiency_hit(prof, dex)

        if not stat_manager.check_hit(user, target, base=chance) or roll_evade(user, target):
            return CombatResult(
                actor=user,
                target=target,
                message=f"{user.key}'s kick misses {target.key}.",
            )

        str_val = stat_manager.get_effective_stat(user, "STR")
        dmg = int(self.base_damage + str_val * 0.2)

        if hasattr(target, "at_damage"):
            target.at_damage(user, dmg, DamageType.BLUDGEONING)
        elif hasattr(target, "hp"):
            target.hp = max(target.hp - dmg, 0)

        return CombatResult(
            actor=user,
            target=target,
            message=f"{user.key} kicks {target.key} for {dmg} damage!",
        )
