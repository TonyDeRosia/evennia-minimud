"""Extended mob AI behaviors inspired by CircleMUD."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable
from random import choice, randint

from evennia import DefaultObject
from evennia.utils import logger
from typeclasses.npcs import BaseNPC
from combat.combat_ai.npc_logic import npc_take_turn


@dataclass
class MemoryRecord:
    """Simple memory record for mob aggression."""

    account_id: int


def remember(npc: DefaultObject, player: DefaultObject) -> None:
    """Remember ``player`` for later retaliation."""
    if not player or not player.account:
        return
    mem = npc.db.memory or []
    acc_id = player.account.id
    if acc_id not in mem:
        mem.append(acc_id)
        npc.db.memory = mem


def forget(npc: DefaultObject, player: DefaultObject) -> None:
    """Forget ``player`` if previously remembered."""
    if not player or not player.account:
        return
    mem = npc.db.memory or []
    acc_id = player.account.id
    if acc_id in mem:
        mem.remove(acc_id)
        npc.db.memory = mem


def clear_memory(npc: DefaultObject) -> None:
    """Erase all stored memory."""
    npc.db.memory = []


# ------------------------------------------------------------
# Special function registry
# ------------------------------------------------------------
_SPECIAL_FUNCS: dict[str, Callable[[DefaultObject], bool]] = {}


def register_special(name: str, func: Callable[[DefaultObject], bool]):
    """Register a special function by ``name``."""
    _SPECIAL_FUNCS[name] = func


def _run_specials(npc: BaseNPC) -> bool:
    """Run registered special functions and return True if one handled AI."""
    specials = npc.db.special_funcs or []
    for name in specials:
        func = _SPECIAL_FUNCS.get(name)
        if not func:
            continue
        try:
            if func(npc):
                return True
        except Exception as err:  # pragma: no cover - log errors
            logger.log_err(f"Special func {name} on {npc} failed: {err}")
    return False


# ------------------------------------------------------------
# Helper behaviors
# ------------------------------------------------------------

def _scavenge(npc: BaseNPC) -> None:
    """Pick up the most valuable item in the room."""
    if not npc.location or randint(0, 10):
        return
    items = [obj for obj in npc.location.contents if obj.access(npc, "get")]
    if not items:
        return
    best = max(items, key=lambda o: getattr(o.db, "value", 0))
    best.move_to(npc, quiet=True)
    npc.location.msg_contents(f"{npc.key} gets {best.key}.")


def _roam(npc: BaseNPC) -> None:
    """Move randomly if allowed."""

    flags = set(npc.db.actflags or [])

    if "wander" not in flags:
        return
    if "sentinel" in flags:
        return

    if not npc.location:
        return

    exits = npc.location.contents_get(content_type="exit")
    if not exits:
        return

    valid_exits = list(exits)

    if "stay_area" in flags and npc.db.area_tag:
        valid_exits = []
        for ex in exits:
            dest = ex.destination
            if not dest:
                continue
            dest_area = getattr(dest.db, "area", None)
            if not dest_area:
                dest_area = dest.tags.get(category="area")
            if dest_area == npc.db.area_tag:
                valid_exits.append(ex)

    if not valid_exits:
        return

    exit_obj = choice(valid_exits)
    exit_obj.at_traverse(npc, exit_obj.destination)


def _aggressive(npc: BaseNPC) -> bool:
    """Attack the first valid player."""
    flags = set(npc.db.actflags or [])
    if "aggressive" not in flags or not npc.location:
        return False
    for obj in npc.location.contents:
        if obj.has_account and obj.access(npc, "attack"):
            npc.enter_combat(obj)
            return True
    return False


def _memory_attack(npc: BaseNPC) -> bool:
    """Attack any remembered player found in the room."""
    mem = npc.db.memory or []
    if not mem or not npc.location:
        return False
    for obj in npc.location.contents:
        if obj.has_account and obj.account.id in mem:
            npc.enter_combat(obj)
            return True
    return False


def _charm_rebellion(npc: BaseNPC) -> None:
    """Check for rebellion of charmed mobs."""
    master = npc.db.charmed_by
    if not master:
        return
    minions: Iterable = master.db.charmed_mobs or []
    limit = max((master.db.charisma or 0) - 2, 0) // 3
    if len(minions) > limit and randint(1, 20) > 10:
        npc.enter_combat(master)
        minions = [m for m in minions if m and m != npc]
        master.db.charmed_mobs = minions
        npc.db.charmed_by = None


def _assist_allies(npc: BaseNPC) -> None:
    """Join combat to assist allies."""
    flags = set(npc.db.actflags or [])
    if "assist" not in flags or not npc.location:
        return
    for obj in npc.location.contents:
        if obj is npc or not isinstance(obj, BaseNPC):
            continue
        target = getattr(obj.db, "combat_target", None)
        if obj.in_combat and target and not npc.in_combat:
            npc.enter_combat(target)
            break


def _call_for_help(npc: BaseNPC) -> None:
    """Request aid from allies when in combat."""

    flags = set(npc.db.actflags or [])
    called = npc.ndb.get("called_for_help")

    if "call_for_help" not in flags:
        if called:
            del npc.ndb.called_for_help
        return

    if not npc.in_combat:
        if called:
            del npc.ndb.called_for_help
        return

    if called:
        return

    npc.ndb.called_for_help = True
    if not npc.location:
        return

    npc.location.msg_contents(f"{npc.key} calls for help!")
    target = npc.db.combat_target
    if not target:
        return
    for obj in npc.location.contents:
        if obj is npc or not isinstance(obj, BaseNPC):
            continue
        if obj.in_combat:
            continue
        if "assist" in set(obj.db.actflags or []):
            obj.enter_combat(target)



def _check_wimpy(npc: BaseNPC) -> bool:
    """Flee combat if health is low and the mob is wimpy."""

    flags = set(npc.db.actflags or [])
    if "wimpy" not in flags:
        return False
    if not npc.in_combat:
        return False

    threshold = npc.db.get("flee_at")
    if threshold is None:
        maxhp = npc.max_hp or 0
        threshold = int(maxhp * 0.25)

    if npc.hp <= threshold:
        npc.execute_cmd("flee")
        return True
    return False


# ------------------------------------------------------------
# Main AI entry
# ------------------------------------------------------------

def process_mob_ai(npc: BaseNPC) -> None:
    """Process one AI step for ``npc``."""
    if _run_specials(npc):
        return

    _assist_allies(npc)
    _call_for_help(npc)
    if _check_wimpy(npc):
        return

    if npc.in_combat and npc.db.combat_target:
        npc_take_turn(None, npc, npc.db.combat_target)
        return

    _scavenge(npc)
    _roam(npc)

    if _aggressive(npc):
        return

    _memory_attack(npc)
    _charm_rebellion(npc)
