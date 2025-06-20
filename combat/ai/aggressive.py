from __future__ import annotations

from combat.ai import BaseAI, register_ai
from combat.combat_ai.npc_logic import npc_take_turn


@register_ai("aggressive")
class AggressiveAI(BaseAI):
    """Attack the first player seen or continue fighting."""

    def execute(self, npc):
        if npc.in_combat and npc.db.combat_target:
            npc_take_turn(None, npc, npc.db.combat_target)
            return
        if not npc.location:
            return
        for obj in npc.location.contents:
            if getattr(obj, "has_account", False):
                npc.enter_combat(obj)
                break
