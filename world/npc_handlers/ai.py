"""Basic AI behavior helpers for NPCs."""

from __future__ import annotations

from random import choice
from evennia import DefaultObject
from typeclasses.npcs import BaseNPC


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
    """Run a custom callback stored on the NPC."""
    callback = npc.db.ai_script
    if not callback:
        return
    try:
        if callable(callback):
            callback(npc)
        elif isinstance(callback, str):
            module, func = callback.rsplit(".", 1)
            mod = __import__(module, fromlist=[func])
            getattr(mod, func)(npc)
    except Exception as err:  # pragma: no cover - log errors
        from evennia.utils import logger

        logger.log_err(f"Scripted AI error on {npc}: {err}")


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

    handler = _AI_MAP.get(ai_type.lower())
    if handler:
        handler(npc)
