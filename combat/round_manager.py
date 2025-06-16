"""Combat round management across all active combats."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set

from evennia.utils import delay
from evennia.utils.logger import log_trace
from .engine import _current_hp


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

    def add_combatant(self, combatant, **kwargs) -> bool:
        """Add ``combatant`` to this combat instance."""
        if not self.engine:
            raise RuntimeError("Combat engine failed to initialize")
        if _current_hp(combatant) <= 0:
            return False
        current = {p.actor for p in self.engine.participants}
        if combatant in current:
            return True
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
        if not self.is_valid():
            self.end_combat("Invalid combat instance")
            return
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

        fighters = [p.actor for p in self.engine.participants]

        active_fighters = []
        for fighter in fighters:
            if not fighter:
                continue
            hp = _current_hp(fighter)
            if hp <= 0:
                continue
            # check combat status using the persistent db attribute
            in_combat = getattr(fighter.db, "in_combat", False)
            if in_combat:
                active_fighters.append(fighter)

        return len(active_fighters) >= 2

    def sync_participants(self) -> None:
        """Keep engine participants aligned with room fighters and remove defeated combatants."""
        if not self.engine:
            self.end_combat("No fighters available")
            return

        fighters = set(self.combatants)

        current = {p.actor for p in self.engine.participants}

        # Add new fighters
        for actor in fighters - current:
            self.engine.add_participant(actor)

        # Remove fighters no longer present in the combatants set
        for actor in current - fighters:
            self.engine.remove_participant(actor)

        # Remove defeated combatants
        for actor in list(fighters):
            if _current_hp(actor) <= 0:
                if hasattr(actor, "db"):
                    actor.db.in_combat = False
                self.engine.remove_participant(actor)
                self.combatants.discard(actor)

    def process_round(self) -> None:
        """Process a single combat round for this instance."""
        if self.combat_ended:
            return

        self.round_number += 1
        self.last_round_time = time.time()

        try:
            self.sync_participants()

            if not self.has_active_fighters():
                self.end_combat("No active fighters remaining")
                return

            # Use engine's process_round if available
            if hasattr(self.engine, "process_round"):
                self.engine.process_round()
            else:
                self._manual_round_processing()

            self.sync_participants()

            if not self.has_active_fighters():
                self.end_combat("No active fighters remaining")
                return

            self._schedule_tick()

        except Exception as err:
            log_trace(f"Error in combat round processing: {err}")
            self.end_combat(f"Combat ended due to error: {err}")

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
                self._npc_auto_attack(fighter)

    def _npc_auto_attack(self, npc) -> None:
        """Handle NPC automatic attacks."""
        if not npc or not hasattr(npc, "location"):
            return

        fighters = [p.actor for p in self.engine.participants]
        targets = []
        
        for fighter in fighters:
            if (
                fighter != npc
                and hasattr(fighter, "has_account")
                and fighter.has_account
                and _current_hp(fighter) > 0
                and getattr(fighter, "in_combat", False)
            ):
                targets.append(fighter)

        if not targets:
            return

        target = targets[0]
        if hasattr(npc, "attack"):
            try:
                npc.attack(target)
            except Exception as e:
                log_trace(f"NPC {npc.key} attack failed: {e}")

    def end_combat(self, reason: str = "") -> None:
        """Mark this instance as ended and clean up fighter states."""
        if self.combat_ended:
            return

        self.combat_ended = True
        self.cancel_tick()
        CombatRoundManager.get().remove_combat(self.combat_id)

        # Clean up fighter states
        if self.engine:
            fighters = [p.actor for p in self.engine.participants]

            for fighter in fighters:
                if fighter and hasattr(fighter, "db"):
                    fighter.db.in_combat = False

        if reason:
            log_trace(f"Combat ended: {reason}")


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
            from .engine import CombatEngine
        except ImportError as err:
            raise ImportError("Combat engine could not be imported") from err

        engine = CombatEngine(fighters, round_time=None)
        if not engine:
            raise RuntimeError("CombatEngine failed to initialize")

        combat_id = self._next_id
        self._next_id += 1

        inst = CombatInstance(combat_id, engine, set(fighters), round_time or 2.0)
        self.combats[combat_id] = inst
        for fighter in fighters:
            self.combatant_to_combat[fighter] = combat_id

        inst.start()

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
        return self.combats.get(cid)

    def start_combat(self, combatants: List[object]) -> CombatInstance:
        """Start combat for the given ``combatants``."""
        for combatant in combatants:
            inst = self.get_combatant_combat(combatant)
            if inst:
                for c in combatants:
                    if c not in inst.combatants:
                        inst.add_combatant(c)
                        self.combatant_to_combat[c] = inst.combat_id
                inst.start()
                return inst
        return self.create_combat(combatants)


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
