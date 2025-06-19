"""Threat tracking helpers."""

from __future__ import annotations

from typing import Dict, Iterable, List

from world.system import state_manager
from ..combat_utils import award_xp


class AggroTracker:
    """Track hostility between combatants."""

    def __init__(self) -> None:
        self.table: Dict[object, Dict[object, int]] = {}

    def track(self, target, attacker) -> None:
        if not target or target is attacker:
            return
        if getattr(target, "pk", None) is None or getattr(attacker, "pk", None) is None:
            return
        data = self.table.setdefault(target, {})
        threat = 1 + state_manager.get_effective_stat(attacker, "threat")
        data[attacker] = data.get(attacker, 0) + threat

    def contributors(self, victim, active: Iterable[object]) -> List[object]:
        contributors = list(self.table.get(victim, {}).keys())
        return [c for c in contributors if c in active]

    def award_experience(self, attacker, victim, active: Iterable[object]) -> None:
        if hasattr(victim, "db"):
            exp = getattr(victim.db, "xp_reward", None)
            if exp is None:
                exp = getattr(victim.db, "exp_reward", 0)
        else:
            exp = 0
        exp = int(exp or 0)
        if not exp:
            level = getattr(getattr(victim, "db", None), "level", 1) or 1
            exp = level * 5

        exp = state_manager.calculate_xp_reward(attacker, victim, exp)

        contributors = self.contributors(victim, active) or [attacker]
        award_xp(attacker, exp, contributors)

