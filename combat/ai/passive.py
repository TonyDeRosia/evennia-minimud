from __future__ import annotations

from combat.ai import BaseAI, register_ai


@register_ai("passive")
class PassiveAI(BaseAI):
    """Non-responsive AI that takes no actions."""

    def execute(self, npc):
        return
