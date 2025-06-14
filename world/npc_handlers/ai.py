"""Basic AI behavior helpers for NPCs."""

from __future__ import annotations

from evennia import DefaultObject
from typeclasses.npcs import BaseNPC
from combat.ai import get_ai_class


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

    if "call_for_help" in flags and npc.in_combat and not npc.ndb.get("called_for_help"):
        npc.ndb.called_for_help = True
        if npc.location:
            npc.location.msg_contents(f"{npc.key} calls for help!")
            target = npc.db.combat_target
            if target:
                for obj in npc.location.contents:
                    if obj is npc or not isinstance(obj, BaseNPC):
                        continue
                    if obj.in_combat:
                        continue
                    if "assist" in set(obj.db.actflags or []):
                        obj.enter_combat(target)

    ai_cls = get_ai_class(ai_type.lower())
    if ai_cls:
        ai_cls().execute(npc)
