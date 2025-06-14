from __future__ import annotations

from combat.ai import BaseAI, register_ai
from combat.ai_combat import npc_take_turn


@register_ai("defensive")
class DefensiveAI(BaseAI):
    """Attack only when already in combat."""

    def execute(self, npc):
        if npc.in_combat and npc.db.combat_target:
            npc_take_turn(None, npc, npc.db.combat_target)
