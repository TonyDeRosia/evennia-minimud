from __future__ import annotations

import logging
from typing import Tuple

from ..damage_types import DamageType
from ..combat_utils import roll_evade, roll_parry, roll_block, roll_damage
from typeclasses.gear import BareHand
from utils import roll_dice_string
from world.system import state_manager, stat_manager

logger = logging.getLogger(__name__)


class CombatMath:
    """Helper methods for calculating hit chance and damage."""

    @staticmethod
    def calculate_unarmed_hit(attacker) -> int:
        """Return the hit chance percentage for an unarmed attack."""

        dex = state_manager.get_effective_stat(attacker, "DEX")
        luck = state_manager.get_effective_stat(attacker, "LUCK")
        best = max(
            state_manager.get_effective_stat(attacker, "STR"),
            state_manager.get_effective_stat(attacker, "INT"),
            state_manager.get_effective_stat(attacker, "WIS"),
        )
        profs = getattr(getattr(attacker, "db", None), "proficiencies", {}) or {}
        prof_bonus = max(profs.get("Unarmed", 0), profs.get("Hand-to-Hand", 0))

        chance = 50 + dex * 0.15 + best * 0.10 + luck * 0.10 + prof_bonus
        return int(max(5, min(95, round(chance))))

    @staticmethod
    def check_hit(attacker, target, bonus: float = 0.0) -> Tuple[bool, str]:
        """Return ``(True, '')`` on hit or ``(False, message)`` on failure."""
        base = 85 + int(bonus)
        if not stat_manager.check_hit(attacker, target, base=base):
            return False, f"{attacker.key} misses."
        if roll_evade(attacker, target, base=20):
            return False, f"{target.key} evades the attack!"
        if roll_parry(attacker, target, base=20):
            return False, f"{target.key} parries the attack!"
        if roll_block(attacker, target, base=20):
            return False, f"{target.key} blocks the attack!"
        return True, ""

    @staticmethod
    def calculate_damage(attacker, weapon, target) -> Tuple[int, object, object]:
        """Return ``(damage, damage_type, location)`` for ``weapon`` hitting ``target``."""
        dmg = 0
        dtype = DamageType.BLUDGEONING
        location = None

        hp_trait = getattr(getattr(target, "traits", None), "health", None)
        if hasattr(target, "hp") or hp_trait:
            dmg_bonus = 0

            # Unarmed damage when no weapon is wielded
            unarmed_attack = (
                (isinstance(weapon, BareHand) or weapon is attacker)
                and not getattr(attacker, "wielding", [])
                and not getattr(getattr(attacker, "db", None), "natural_weapon", None)
            )

            if unarmed_attack:
                try:
                    dmg = roll_dice_string("1d6")
                except Exception:
                    logger.error("Invalid dice roll for unarmed damage")
                    dmg = 0
            elif isinstance(weapon, dict):
                dmg = weapon.get("damage")
                dtype = weapon.get("damage_type") or DamageType.BLUDGEONING
                if dmg is None:
                    dice = weapon.get("damage_dice")
                    if dice:
                        try:
                            num, sides = map(int, str(dice).lower().split("d"))
                            dmg = roll_damage((num, sides))
                        except (TypeError, ValueError):
                            logger.error("Invalid damage_dice '%s' on %s", dice, weapon)
                            dmg = 0
                dmg_bonus = int(weapon.get("damage_bonus", 0) or 0)

            else:
                dmg = getattr(weapon, "damage", None)
                dtype = getattr(weapon, "damage_type", None) or DamageType.BLUDGEONING

                if dmg is None:
                    db = getattr(weapon, "db", None)
                    if db:
                        dmg_map = getattr(db, "damage", None)
                        if dmg_map:
                            for i, (dt, formula) in enumerate(
                                sorted(dmg_map.items(), key=lambda kv: str(kv[0]))
                            ):
                                try:
                                    roll = roll_dice_string(str(formula))
                                except Exception:
                                    logger.error("Invalid damage formula '%s' on %s", formula, weapon)
                                    roll = 0
                                dmg = dmg + roll if dmg else roll
                                if i == 0:
                                    dtype = dt
                        else:
                            dice = getattr(db, "damage_dice", None) or "2d6"
                            try:
                                dmg = roll_dice_string(str(dice))
                            except Exception:
                                logger.error("Invalid damage_dice '%s' on %s", dice, weapon)
                                dmg = int(getattr(db, "dmg", 0))
                        dmg_bonus = int(getattr(db, "damage_bonus", 0) or 0)


            # Final safety check
            if dmg is None:
                dmg = 0

            dmg += dmg_bonus

            # Apply unarmed proficiency scaling if not wielding a weapon
            if not getattr(attacker, "wielding", []):
                from world.skills.unarmed_passive import Unarmed
                from world.skills.hand_to_hand import HandToHand

                skills = getattr(attacker.db, "skills", []) or []
                profs = getattr(attacker.db, "proficiencies", {}) or {}
                bonus_pct = 0.0
                for cls in (HandToHand, Unarmed):
                    if cls.name in skills:
                        pct = profs.get(cls.name, 0) * cls.dmg_scale
                        bonus_pct = max(bonus_pct, pct)
                dmg = int(round(dmg * (1 + bonus_pct / 100)))

            # Scale with stats
            str_val = state_manager.get_effective_stat(attacker, "STR")
            dex_val = state_manager.get_effective_stat(attacker, "DEX")
            dmg = int(round(dmg * (1 + str_val * 0.05 + dex_val * 0.02)))

            from ..body_parts import DEFAULT_HIT_LOCATIONS
            import random
            location = random.choice(DEFAULT_HIT_LOCATIONS)
            dmg = int(round(dmg * location.damage_mod))

        return dmg, dtype, location

    @staticmethod
    def apply_critical(attacker, target, damage: int) -> Tuple[int, bool]:
        """Apply critical hit logic to ``damage`` and return ``(damage, crit)``."""
        crit = stat_manager.roll_crit(attacker, target)
        if crit:
            damage = stat_manager.crit_damage(attacker, damage)
        return damage, crit
