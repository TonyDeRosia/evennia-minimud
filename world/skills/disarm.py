from combat.combat_actions import CombatResult
from combat.combat_utils import roll_evade, roll_parry
from world.system import stat_manager
from .skill import Skill


class Disarm(Skill):
    """Attempt to knock the target's weapon from their hands."""

    name = "disarm"
    cooldown = 5
    stamina_cost = 5

    def resolve(self, user, target):
        """Try to disarm ``target``."""
        self.improve(user)
        weapon = target.wielding[0] if getattr(target, "wielding", []) else None
        if not weapon:
            return CombatResult(
                actor=user,
                target=target,
                message=f"{target.key} isn't wielding anything.",
            )
        if (
            not stat_manager.check_hit(user, target)
            or roll_evade(user, target)
            or roll_parry(user, target)
        ):
            return CombatResult(
                actor=user,
                target=target,
                message=f"{user.key}'s disarm attempt fails against {target.key}.",
            )
        target.at_unwield(weapon)
        return CombatResult(
            actor=user,
            target=target,
            message=f"$You() disarm(s) {target.key}, knocking {weapon.key} away!",
        )
