from __future__ import annotations

import logging
from typing import Tuple

from ..damage_types import DamageType
from ..combat_utils import roll_damage, roll_evade, roll_parry, roll_block
from utils import roll_dice_string
from world.system import state_manager, stat_manager

logger = logging.getLogger(__name__)


def check_hit(attacker, target) -> Tuple[bool, str]:
    """Return ``(True, '')`` on hit or ``(False, message)`` on failure."""
    if not stat_manager.check_hit(attacker, target):
        return False, f"{attacker.key} misses."
    if roll_evade(attacker, target):
        return False, f"{target.key} evades the attack!"
    if roll_parry(attacker, target):
        return False, f"{target.key} parries the attack!"
    if roll_block(attacker, target):
        return False, f"{target.key} blocks the attack!"
    return True, ""


def calculate_damage(attacker, weapon, target) -> Tuple[int, object]:
    """Return ``(damage, damage_type)`` for ``weapon`` hitting ``target``."""
    dmg = 0
    dtype = DamageType.BLUDGEONING

    hp_trait = getattr(getattr(target, "traits", None), "health", None)
    if hasattr(target, "hp") or hp_trait:
        if isinstance(weapon, dict):
            dmg = weapon.get("damage")
            dtype = weapon.get("damage_type", DamageType.BLUDGEONING)
        else:
            dmg = getattr(weapon, "damage", None)
            dtype = getattr(weapon, "damage_type", DamageType.BLUDGEONING)

        if dmg is None:
            db = getattr(weapon, "db", None)
            if db:
                dmg_map = getattr(db, "damage", None)
                if dmg_map:
                    for i, (dt, formula) in enumerate(dmg_map.items()):
                        try:
                            roll = roll_dice_string(str(formula))
                        except Exception:
                            logger.error("Invalid damage formula '%s' on %s", formula, weapon)
                            roll = 0
                        dmg = dmg + roll if dmg else roll
                        if i == 0:
                            dtype = dt
                else:
                    dice = getattr(db, "damage_dice", None)
                    if dice:
                        try:
                            num, sides = map(int, str(dice).lower().split("d"))
                        except (TypeError, ValueError):
                            logger.error("Invalid damage_dice '%s' on %s", dice, weapon)
                            dmg = int(getattr(db, "dmg", 0))
                        else:
                            dmg = roll_damage((num, sides))
                    else:
                        dmg = int(getattr(db, "dmg", 0))

        if dmg is None:
            dmg = 0

        str_val = state_manager.get_effective_stat(attacker, "STR")
        dex_val = state_manager.get_effective_stat(attacker, "DEX")
        dmg = int(round(dmg * (1 + str_val * 0.012 + dex_val * 0.004)))

    return dmg, dtype


def apply_critical(attacker, target, damage: int) -> Tuple[int, bool]:
    """Apply critical hit logic to ``damage`` and return ``(damage, crit)``."""
    crit = stat_manager.roll_crit(attacker, target)
    if crit:
        damage = stat_manager.crit_damage(attacker, damage)
    return damage, crit
