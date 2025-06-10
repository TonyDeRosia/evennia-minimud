"""Basic AI behavior helpers for NPCs."""

from __future__ import annotations

from random import choice
from importlib import import_module
from evennia import DefaultObject
from evennia.utils import logger
from typeclasses.npcs import BaseNPC
from combat.ai_combat import npc_take_turn


ALLOWED_CALLBACK_MODULES = ("scripts",)


def _import_ai_callback(path: str):
    """Import the AI callback if within allowed modules."""
    module, func = path.rsplit(".", 1)
    if not any(
        module == allowed or module.startswith(f"{allowed}.")
        for allowed in ALLOWED_CALLBACK_MODULES
    ):
        raise ImportError(f"Module '{module}' is not allowed")
    mod = import_module(module)
    return getattr(mod, func)


def _ai_aggressive(npc: DefaultObject) -> None:
    """Aggressive behavior: enter combat or act if already fighting."""
    if npc.in_combat and npc.db.combat_target:
        npc_take_turn(None, npc, npc.db.combat_target)
        return
    if not npc.location:
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
        npc_take_turn(None, npc, npc.db.combat_target)


def _ai_scripted(npc: DefaultObject) -> None:
    """Run a custom callback stored on the NPC."""
    callback = npc.db.ai_script
    if not callback:
        return
    try:
        if callable(callback):
            callback(npc)
        elif isinstance(callback, str):
            try:
                func = _import_ai_callback(callback)
            except Exception as err:
                logger.log_err(f"Scripted AI import rejected on {npc}: {err}")
                return
            func(npc)
    except Exception as err:  # pragma: no cover - log errors
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
