"""Kick skill definition."""

from combat.combat_utils import roll_evade, format_combat_message, highlight_keywords
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
        """Resolve the kick immediately, applying damage to the target."""
        from combat.combat_actions import CombatResult

        self.improve(user)

        profs = user.db.proficiencies or {}
        prof = profs.get(self.name, 0)
        dex = stat_manager.get_effective_stat(user, "DEX")
        str_val = stat_manager.get_effective_stat(user, "STR")

        chance = stat_manager.proficiency_hit(prof, dex)
        hit = stat_manager.check_hit(user, target, base=chance)
        evade = roll_evade(user, target)

        if not hit or evade:
            msg = format_combat_message(user, target, "kick", miss=True)
            return CombatResult(actor=user, target=target, message=highlight_keywords(msg))

        dmg = int(self.base_damage + str_val * 0.2)

        if hasattr(target, "at_damage"):
            target.at_damage(user, dmg, DamageType.BLUDGEONING)
        elif hasattr(target, "hp"):
            target.hp = max(target.hp - dmg, 0)

        msg = format_combat_message(user, target, "kicks", dmg)
        return CombatResult(actor=user, target=target, message=highlight_keywords(msg))
