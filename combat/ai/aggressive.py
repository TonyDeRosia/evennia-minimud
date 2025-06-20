from __future__ import annotations

from combat.ai import BaseAI, register_ai
from combat.ai_combat import queue_npc_action


@register_ai("aggressive")
class AggressiveAI(BaseAI):
    """Attack the first player seen or continue fighting."""

    def execute(self, npc):
        if npc.in_combat and npc.db.combat_target:
            queue_npc_action(None, npc, npc.db.combat_target)
            return
        if not npc.location:
            return
        for obj in npc.location.contents:
            if getattr(obj, "has_account", False):
                npc.enter_combat(obj)
                break
