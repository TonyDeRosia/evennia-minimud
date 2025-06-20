from __future__ import annotations

from combat.ai import BaseAI, register_ai
from combat.ai_combat import queue_npc_action


@register_ai("defensive")
class DefensiveAI(BaseAI):
    """Attack only when already in combat."""

    def execute(self, npc):
        if npc.in_combat and npc.db.combat_target:
            queue_npc_action(None, npc, npc.db.combat_target)
