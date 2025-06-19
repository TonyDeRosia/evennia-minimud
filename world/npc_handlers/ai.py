"""Basic AI behavior helpers for NPCs."""

from __future__ import annotations

from evennia import DefaultObject
from typeclasses.npcs import BaseNPC
from combat.ai import get_ai_class
from .mob_ai import _call_for_help


def process_ai(npc: DefaultObject) -> None:
    """Process one AI step for ``npc``."""
    ai_type = npc.db.ai_type
    if not ai_type:
        return
    flags = set(npc.db.actflags or [])

    if "assist" in flags:
        leader = npc.db.following
        if leader and leader.location == npc.location:
            target = getattr(leader.db, "combat_target", None)
            if leader.in_combat and target and not npc.in_combat:
                npc.enter_combat(target)

    _call_for_help(npc)

    ai_cls = get_ai_class(ai_type.lower())
    if ai_cls:
        ai_cls().execute(npc)
