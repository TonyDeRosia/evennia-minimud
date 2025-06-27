"""Combat round management across all active combats.

This is the primary combat loop manager. The old `combat.combat_manager` module
re-exports these classes for backward compatibility."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set
from django.conf import settings

from evennia.utils import delay
from evennia.utils.logger import log_trace, log_info
import logging
from combat.combatants import _current_hp
from combat.events import combat_started, round_processed, combat_ended

logger = logging.getLogger(__name__)


@dataclass
class CombatInstance:
    """Container representing a single combat encounter."""

    combat_id: int
    engine: object  # CombatEngine
    combatants: Set[object]
    round_time: float = 2.0
    round_number: int = 0
    last_round_time: float = field(default_factory=time.time)
    combat_ended: bool = False
    tick_handle: Optional[object] = field(default=None, init=False, repr=False)
    room: Optional[object] = field(default=None, init=False, repr=False)

    def add_combatant(self, combatant, **kwargs) -> bool:
        """Add ``combatant`` to this combat instance."""
        if not self.engine:
            raise RuntimeError("Combat engine failed to initialize")
        if _current_hp(combatant) <= 0:
            return False
        current = {p.actor for p in self.engine.participants}
        if combatant in current:
            return True
        if self.room is None:
            self.room = getattr(combatant, "location", None)
        self.combatants.add(combatant)
        self.engine.add_participant(combatant)
        return True

    def remove_combatant(self, combatant, **kwargs) -> bool:
        """Remove ``combatant`` from this combat instance."""
        if not self.engine:
            return False
        self.engine.remove_participant(combatant)
        self.combatants.discard(combatant)
        try:
            CombatRoundManager.get().combatant_to_combat.pop(combatant, None)
        except Exception:  # pragma: no cover - safety
            pass
        return True

    # ------------------------------------------------------------------
    # ticking helpers
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Begin automatic round processing."""
        self._schedule_tick()

    def _schedule_tick(self) -> None:
        """Schedule the next combat round."""
        if self.combat_ended or self.tick_handle:
            return
        if settings.COMBAT_DEBUG_TICKS:
            logger.debug(
                "Scheduling combat tick %s in %s seconds",
                self.round_number + 1,
                self.round_time,
            )
        self.tick_handle = delay(self.round_time, self._tick)

    def cancel_tick(self) -> None:
        """Cancel any pending tick."""
        if self.tick_handle:
            try:
                self.tick_handle.cancel()
            except Exception:  # pragma: no cover - safety
                pass
            self.tick_handle = None

    def _tick(self) -> None:
        """Process a round and schedule the next one."""
        self.tick_handle = None
        if settings.COMBAT_DEBUG_TICKS:
            logger.debug("Combat tick %s executed", self.round_number)
        if not self.is_valid():
            self.end_combat("Invalid combat instance")
            return

        # Sync and process any defeated combatants before checking active fighters
        try:
            self.sync_participants()
        except Exception as err:  # pragma: no cover - safety
            log_trace(f"Error syncing participants: {err}")

        if not self.has_active_fighters():
            self.end_combat("No active fighters remaining")
            return

        self.process_round()

    def is_valid(self) -> bool:
        """Return ``True`` if this instance is still active."""
        return bool(self.combatants) and not self.combat_ended

    def has_active_fighters(self) -> bool:
        """Return ``True`` if at least two participants can still fight."""
        if not self.engine:
            return False

        fighters = {p.actor for p in self.engine.participants}
        fighters.update(self.combatants)

        active_fighters = []
        fighter_info = []
        for fighter in fighters:
            if not fighter:
                continue
            hp = _current_hp(fighter)
            # safely check combat status using persistent db attribute first
            in_combat = getattr(getattr(fighter, "db", None), "in_combat", None)
            if in_combat is None:
                in_combat = getattr(fighter, "in_combat", False)
            fighter_info.append((fighter, hp, in_combat))
            if hp > 0 and (in_combat is True or fighter in self.combatants):
                active_fighters.append(fighter)

        for fighter, hp, in_combat in fighter_info:
            logger.debug(
                "Fighter status: %s - HP: %s, in_combat: %s",
                getattr(fighter, "key", fighter),
                hp,
                in_combat,
            )

        return len(active_fighters) >= 2

    def sync_participants(self) -> None:
        """Keep engine participants aligned with room fighters and remove defeated combatants."""
        if not self.engine:
            self.end_combat("No fighters available")
            return

        fighters = set(self.combatants)
        current = {p.actor for p in self.engine.participants}

        self._add_new_fighters(fighters, current)
        self._remove_missing_fighters(fighters, current)
        self._remove_defeated_fighters(fighters)

    def _add_new_fighters(self, fighters: Set[object], current: Set[object]) -> None:
        """Register any fighters missing from the combat engine."""
        for actor in fighters - current:
            self.engine.add_participant(actor)
            if getattr(actor, "pk", None) is None:
                setattr(actor, "in_combat", True)

    def _remove_missing_fighters(self, fighters: Set[object], current: Set[object]) -> None:
        """Remove engine participants no longer present in this instance."""
        for actor in current - fighters:
            self.engine.remove_participant(actor)
            if getattr(actor, "pk", None) is None:
                setattr(actor, "in_combat", False)

    def _remove_defeated_fighters(self, fighters: Set[object]) -> None:
        """Handle any fighters that have been defeated."""
        for actor in list(fighters):
            if _current_hp(actor) <= 0 and not getattr(getattr(actor, "db", None), "is_dead", False):
                log = getattr(getattr(actor, "ndb", None), "damage_log", None) or {}
                killer = max(log, key=log.get) if log else None
                try:
                    self.engine.handle_defeat(actor, killer)
                except Exception as err:  # pragma: no cover - safety
                    log_trace(f"Error handling defeat of {getattr(actor, 'key', actor)}: {err}")

    def process_round(self) -> None:
        """Process a single combat round for this instance."""
        if self.combat_ended:
            return

        self.round_number += 1
        self.last_round_time = time.time()

        try:
            if not self._validate_fighters():
                return

            # Use engine's process_round if available
            if hasattr(self.engine, "process_round"):
                self.engine.process_round()
            else:
                self._manual_round_processing()

            self._finalize_round()

        except Exception as err:
            log_trace(f"Error in combat round processing: {err}")
            self.end_combat(f"Combat ended due to error: {err}")

    def _validate_fighters(self) -> bool:
        """Return ``True`` if combat should continue after syncing fighters."""
        self.sync_participants()
        if not self.has_active_fighters():
            self.end_combat("No active fighters remaining")
            return False
        return True

    def _finalize_round(self) -> None:
        """Finalize round processing and schedule the next tick if valid."""
        round_processed.send(sender=CombatRoundManager, instance=self)
        self.sync_participants()
        if not self.has_active_fighters():
            self.end_combat("No active fighters remaining")
            return
        self._schedule_tick()

    def _manual_round_processing(self) -> None:
        """Fallback round processing if engine doesn't have process_round."""
        fighters = [p.actor for p in self.engine.participants]
        
        for fighter in list(fighters):
            if not fighter or _current_hp(fighter) <= 0:
                continue

            if not getattr(fighter, "in_combat", False):
                continue

            # Handle NPC auto-attacks
            if not hasattr(fighter, "has_account") or not fighter.has_account:
                from combat.ai_combat import auto_attack
                auto_attack(fighter, self.engine)


    def end_combat(self, reason: str = "") -> None:
        """Mark this instance as ended and clean up fighter states."""
        if self.combat_ended:
            return

        # ensure any pending defeat or death logic runs first
        try:
            self.sync_participants()
        except Exception as err:  # pragma: no cover - safety
            log_trace(f"Error syncing participants on end: {err}")

        room = getattr(self, "room", None)
        try:
            if self.engine and self.engine.participants:
                room = getattr(self.engine.participants[0].actor, "location", None)
            if not room and self.combatants:
                fighter = next(iter(self.combatants))
                room = getattr(fighter, "location", None)
        except Exception:  # pragma: no cover - safety
            room = None

        self.cancel_tick()
        CombatRoundManager.get().remove_combat(self.combat_id)

        send_room_msg = True
        if reason == "No active fighters remaining":
            reason = ""
        if reason == "Invalid combat instance":
            try:
                log_info(reason)
            except Exception:
                log_trace(reason)
            reason = ""
            send_room_msg = False

        message = f"Combat ends: {reason}" if reason else "Combat ends."
        if send_room_msg and room and hasattr(room, "msg_contents"):
            try:
                room.msg_contents(message)
            except Exception:  # pragma: no cover - safety
                pass

        # Clean up fighter states
        if self.engine:
            fighters = set(self.combatants)
            fighters.update(p.actor for p in self.engine.participants)

            for fighter in fighters:
                if not fighter:
                    continue
                if hasattr(fighter, "db") and getattr(fighter, "pk", None) is not None:
                    fighter.db.in_combat = False
                    fighter.db.combat_target = None
                else:
                    setattr(fighter, "in_combat", False)
                    setattr(fighter, "combat_target", None)

        if reason:
            log_trace(f"Combat ended: {reason}")

        self.combat_ended = True
        combat_ended.send(sender=CombatRoundManager, instance=self, reason=reason)


class CombatRoundManager:
    """Manage all active combat instances."""

    _instance: Optional["CombatRoundManager"] = None

    def __init__(self) -> None:
        self.combats: Dict[int, CombatInstance] = {}
        self.combatant_to_combat: Dict[object, int] = {}
        self._next_id = 1

    @classmethod
    def get(cls) -> "CombatRoundManager":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # combat management
    # ------------------------------------------------------------------

    def create_combat(
        self, combatants: Optional[List[object]] = None, round_time: Optional[float] = None
    ) -> CombatInstance:
        """Create a new combat with ``combatants``."""

        fighters = combatants or []

        try:
            from combat.engine import CombatEngine
        except ImportError as err:
            raise ImportError("Combat engine could not be imported") from err

        engine = CombatEngine(fighters, round_time=round_time or 2.0)
        if not engine:
            raise RuntimeError("CombatEngine failed to initialize")

        combat_id = self._next_id
        self._next_id += 1

        inst = CombatInstance(combat_id, engine, set(fighters), round_time or 2.0)
        if fighters:
            inst.room = getattr(fighters[0], "location", None)
        self.combats[combat_id] = inst
        for fighter in fighters:
            self.combatant_to_combat[fighter] = combat_id

        inst.start()
        combat_started.send(sender=self.__class__, instance=inst)

        return inst

    def remove_combat(self, combat_id: int) -> None:
        """Remove combat ``combat_id`` from management."""
        inst = self.combats.pop(combat_id, None)
        if not inst:
            return
        for fighter in list(inst.combatants):
            self.combatant_to_combat.pop(fighter, None)

    def get_combatant_combat(self, combatant) -> Optional[CombatInstance]:
        """Return the combat instance ``combatant`` is part of."""
        cid = self.combatant_to_combat.get(combatant)
        if cid is None:
            return None
        inst = self.combats.get(cid)
        if inst and inst.combat_ended:
            # clean up stale reference
            self.combatant_to_combat.pop(combatant, None)
            return None
        return inst

    def start_combat(self, combatants: List[object]) -> CombatInstance:
        """Start combat for the given ``combatants``."""
        # gather any existing combat instances these combatants are part of
        instances = []
        for combatant in combatants:
            inst = self.get_combatant_combat(combatant)
            if inst:
                if inst.combat_ended:
                    # clean up stale references to ended combat
                    self.remove_combat(inst.combat_id)
                    continue
                if inst not in instances:
                    instances.append(inst)

        if not instances:
            # none of the combatants were already fighting
            return self.create_combat(combatants)

        primary = instances[0]

        # merge any additional instances into the primary
        for other in instances[1:]:
            for fighter in list(other.combatants):
                other.remove_combatant(fighter)
                primary.add_combatant(fighter)
                self.combatant_to_combat[fighter] = primary.combat_id
                try:
                    fighter.db.in_combat = True
                except Exception:
                    setattr(fighter, "in_combat", True)
            other.end_combat("Merged into another instance")

        # ensure all provided combatants are in the primary instance
        for combatant in combatants:
            if combatant not in primary.combatants:
                primary.add_combatant(combatant)
                self.combatant_to_combat[combatant] = primary.combat_id

        # flag all fighters and verify engine registration
        current = {p.actor for p in primary.engine.participants}
        for combatant in combatants:
            try:
                combatant.db.in_combat = True
            except Exception:
                setattr(combatant, "in_combat", True)
            if combatant not in current:
                primary.engine.add_participant(combatant)
                current.add(combatant)

        primary.start()
        combat_started.send(sender=self.__class__, instance=primary)
        return primary


    # ------------------------------------------------------------------
    # debugging helpers
    # ------------------------------------------------------------------
    def get_combat_status(self) -> Dict:
        status = {
            "total_instances": len(self.combats),
            "instances": [],
        }

        for inst in self.combats.values():
            fighter_count = len(inst.engine.participants) if inst.engine else 0

            status["instances"].append(
                {
                    "id": inst.combat_id,
                    "round_number": inst.round_number,
                    "fighters": fighter_count,
                    "valid": inst.is_valid(),
                    "has_active_fighters": inst.has_active_fighters(),
                    "ended": inst.combat_ended,
                }
            )
        return status

    def force_end_all_combat(self) -> None:
        """Force end all combat instances."""
        for inst in list(self.combats.values()):
            inst.end_combat("Force ended by admin")
        self.combats.clear()
        self.combatant_to_combat.clear()

    def debug_info(self) -> str:
        """Return formatted debug information about the combat manager."""
        status = self.get_combat_status()
        lines = [
            "Combat Manager Status:",
            f"  Active Instances: {status['total_instances']}",
            "",
        ]

        for i, inst in enumerate(status["instances"]):
            lines.extend(
                [
                    f"  Instance {i + 1}:",
                    f"    ID: {inst['id']}",
                    f"    Round: {inst['round_number']}",
                    f"    Fighters: {inst['fighters']}",
                    f"    Valid: {inst['valid']}",
                    f"    Active: {inst['has_active_fighters']}",
                    f"    Ended: {inst['ended']}",
                    "",
                ]
            )

        return "\n".join(lines)


def leave_combat(chara) -> None:
    """Remove ``chara`` from combat and clear combat state."""

    if not chara:
        return

    manager = CombatRoundManager.get()
    instance = manager.get_combatant_combat(chara)
    if instance:
        instance.remove_combatant(chara)

    if hasattr(chara, "db") and getattr(chara, "pk", None) is not None:
        chara.db.in_combat = False
        chara.db.combat_target = None
    else:
        setattr(chara, "in_combat", False)
        setattr(chara, "combat_target", None)

    if hasattr(chara, "ndb") and hasattr(chara.ndb, "combat_engine"):
        del chara.ndb.combat_engine
    if hasattr(chara, "ndb") and hasattr(chara.ndb, "damage_log"):
        del chara.ndb.damage_log


__all__ = ["CombatInstance", "CombatRoundManager", "leave_combat"]
