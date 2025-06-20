"""Helpers for queuing NPC combat actions."""

from __future__ import annotations

from typing import Any

from combat.engine import CombatEngine
from combat.combat_ai.npc_logic import npc_take_turn as _npc_take_turn


def queue_npc_action(engine: CombatEngine | None, npc: Any, target: Any) -> None:
    """Queue an action for ``npc`` on ``engine``.

    This wraps :func:`combat.combat_ai.npc_logic.npc_take_turn` so that the
    selected action is placed into ``engine``'s queue via
    :meth:`CombatEngine.queue_action`.
    """
    _npc_take_turn(engine, npc, target)

