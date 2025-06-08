"""Basic AI behavior helpers for NPCs."""

from __future__ import annotations

from random import choice
from evennia import DefaultObject


def _ai_aggressive(npc: DefaultObject) -> None:
    """Very simple aggressive behavior: attack the first player here."""
    if not npc.location or npc.in_combat:
        return
    for obj in npc.location.contents:
        if obj.has_account:
            npc.enter_combat(obj)
            break


def _ai_wander(npc: DefaultObject) -> None:
    """Move randomly through available exits."""
    if not npc.location:
        return
    exits = npc.location.contents_get(content_type="exit")
    if exits:
        exit_obj = choice(exits)
        exit_obj.at_traverse(npc, exit_obj.destination)


def _ai_defensive(npc: DefaultObject) -> None:
    """Attack only when already in combat."""
    if npc.in_combat and npc.db.combat_target:
        weapon = npc.wielding[0] if npc.wielding else npc
        npc.attack(npc.db.combat_target, weapon)


def _ai_scripted(npc: DefaultObject) -> None:
    """Placeholder scripted behavior hook."""
    pass


def _ai_passive(npc: DefaultObject) -> None:
    """Non-responsive AI that takes no actions."""
    return


_AI_MAP = {
    "aggressive": _ai_aggressive,
    "wander": _ai_wander,
    "defensive": _ai_defensive,
    "scripted": _ai_scripted,
    "passive": _ai_passive,
}


def process_ai(npc: DefaultObject) -> None:
    """Process one AI step for ``npc``."""
    ai_type = npc.db.ai_type
    if not ai_type:
        return
    handler = _AI_MAP.get(ai_type.lower())
    if handler:
        handler(npc)
