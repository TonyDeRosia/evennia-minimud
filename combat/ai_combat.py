"""Helpers for queuing NPC combat actions."""

from __future__ import annotations

from typing import Any

from evennia.utils.logger import log_trace

from combat.combatants import _current_hp

from combat.combat_ai.npc_logic import npc_take_turn as _npc_take_turn


def queue_npc_action(engine: CombatEngine | None, npc: Any, target: Any) -> None:
    """Queue an action for ``npc`` on ``engine``.

    This wraps :func:`combat.combat_ai.npc_logic.npc_take_turn` so that the
    selected action is placed into ``engine``'s queue via
    :meth:`CombatEngine.queue_action`.
    """
    _npc_take_turn(engine, npc, target)


def auto_attack(npc: Any, engine: Any) -> None:
    """Perform a basic auto attack for ``npc`` using ``engine``.

    This mirrors the manual round auto-attack logic previously
    implemented on :class:`CombatRoundManager`.
    """
    if not npc or not hasattr(npc, "location"):
        return

    fighters = [p.actor for p in engine.participants] if engine else []
    targets = []

    for fighter in fighters:
        if (
            fighter is not npc
            and getattr(fighter, "has_account", False)
            and _current_hp(fighter) > 0
            and getattr(fighter, "in_combat", False)
        ):
            targets.append(fighter)

    if not targets:
        return

    target = targets[0]
    if hasattr(npc, "attack"):
        try:
            npc.attack(target)
        except Exception as err:  # pragma: no cover - safety
            log_trace(f"NPC {getattr(npc, 'key', npc)} attack failed: {err}")

