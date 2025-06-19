from __future__ import annotations

from random import choice

from combat.ai import BaseAI, register_ai


@register_ai("wander")
class WanderAI(BaseAI):
    """Move randomly through available exits."""

    def execute(self, npc):
        flags = set(npc.db.actflags or [])
        if "sentinel" in flags:
            return
        if not npc.location:
            return
        exits = npc.location.contents_get(content_type="exit")
        if exits:
            exit_obj = choice(exits)
            exit_obj.at_traverse(npc, exit_obj.destination)
