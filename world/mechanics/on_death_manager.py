from __future__ import annotations

"""Centralized death handling helpers."""

from evennia.utils import inherits_from, logger
from combat.corpse_creation import spawn_corpse
from combat.round_manager import CombatRoundManager, leave_combat
from world.system import state_manager


def handle_death(victim, killer=None):
    """Handle generic death cleanup for any character."""
    if not victim or getattr(victim, "location", None) is None:
        return None

    if getattr(victim.attributes, "get", lambda *a, **k: None)("_dead"):
        return None

    # mark death flags
    try:
        victim.db._dead = True
        victim.db.dead = True
        victim.db.is_dead = True
    except Exception:
        pass

    manager = CombatRoundManager.get()
    inst = manager.get_combatant_combat(victim)
    engine = inst.engine if inst else None

    # remove from combat
    leave_combat(victim)

    location = victim.location
    corpse = None

    # broadcast messages before converting to a corpse
    if killer:
        victim.msg(f"You are slain by {killer.get_display_name(victim)}!")
        if location:
            location.msg_contents(f"{victim.key} is |Rslain|n by |C{killer.key}|n!")
    else:
        victim.msg("You have died.")
        if location:
            location.msg_contents(f"{victim.key} dies.")

    # experience award before corpse creation so messages appear immediately
    if killer:
        if engine:
            try:
                engine.award_experience(killer, victim)
            except Exception:  # pragma: no cover - safety
                logger.log_trace()
        elif inherits_from(victim, "typeclasses.characters.NPC"):
            exp = int(getattr(victim.db, "exp_reward", 0) or 0)
            if exp:
                exp = state_manager.calculate_xp_reward(killer, victim, exp)
                if exp:
                    if hasattr(killer, "msg"):
                        killer.msg(f"You gain |Y{exp}|n experience points!")
                    state_manager.gain_xp(killer, exp)

    if location:
        corpse = next(
            (
                obj
                for obj in location.contents
                if obj.is_typeclass("typeclasses.objects.Corpse", exact=False)
                and obj.db.corpse_of_id == getattr(victim, "dbref", None)
            ),
            None,
        )
        if not corpse:
            corpse = spawn_corpse(victim, killer)
            if corpse:
                corpse.location = location
                if getattr(victim, "key", None):
                    corpse.db.corpse_of = victim.key
                if getattr(victim, "dbref", None):
                    corpse.db.corpse_of_id = victim.dbref
                if getattr(getattr(victim, "db", None), "vnum", None) is not None:
                    corpse.db.npc_vnum = victim.db.vnum

    # call at_death hooks
    try:
        victim.at_death(killer)
    except Exception:  # pragma: no cover - safety
        logger.log_trace()

    return corpse
