from __future__ import annotations

"""Death handler interface and default implementation."""

from abc import ABC, abstractmethod
from django.conf import settings
from evennia.utils.utils import class_from_module
from evennia.utils import inherits_from, logger

from world.mechanics import corpse_manager
from combat.round_manager import CombatRoundManager, leave_combat
from world.system import state_manager


class IDeathHandler(ABC):
    """Interface for custom death handlers."""

    @abstractmethod
    def handle(self, victim, killer=None):
        """Handle cleanup when ``victim`` dies."""
        raise NotImplementedError


class DefaultDeathHandler(IDeathHandler):
    """Replicates the original death handling logic."""

    def handle(self, victim, killer=None):  # noqa: D401 - simple interface
        if not victim or getattr(victim, "location", None) is None:
            return None

        if getattr(getattr(victim, "attributes", None), "get", lambda *a, **k: None)("_dead"):
            return None

        try:
            victim.db._dead = True
            victim.db.dead = True
            victim.db.is_dead = True
        except Exception:
            pass

        manager = CombatRoundManager.get()
        inst = manager.get_combatant_combat(victim)
        engine = inst.engine if inst else None

        leave_combat(victim)

        location = victim.location
        corpse = None

        if killer:
            victim.msg(f"You are slain by {killer.get_display_name(victim)}!")
            if location:
                location.msg_contents(f"{victim.key} is |Rslain|n by |C{killer.key}|n!")
        else:
            victim.msg("You have died.")
            if location:
                location.msg_contents(f"{victim.key} dies.")

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
                corpse = corpse_manager.create_corpse(victim)
                if inherits_from(victim, "typeclasses.characters.NPC"):
                    corpse_manager.apply_loot(victim, corpse, killer)
                corpse_manager.finalize_corpse(victim, corpse)
                corpse.location = location

        try:
            victim.at_death(killer)
        except Exception:  # pragma: no cover - safety
            logger.log_trace()

        return corpse


def _load_handler():
    path = getattr(settings, "DEATH_HANDLER_CLASS", "world.mechanics.death_handlers.DefaultDeathHandler")
    cls = class_from_module(path)
    return cls()


_handler_instance: IDeathHandler | None = None


def get_handler() -> IDeathHandler:
    """Return the configured death handler instance."""
    global _handler_instance
    if _handler_instance is None:
        _handler_instance = _load_handler()
    return _handler_instance


def set_handler(handler: IDeathHandler) -> None:
    """Set the global death handler instance."""
    global _handler_instance
    _handler_instance = handler
