"""Combat round management across all active combats."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set

from evennia.utils import delay
from evennia.utils.logger import log_trace
from django.conf import settings
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
        return True

    def is_valid(self) -> bool:
        """Return ``True`` if this instance is still active."""
        return bool(self.combatants) and not self.combat_ended

    def has_active_fighters(self) -> bool:
        """Return ``True`` if at least two participants can still fight."""
        if not self.engine:
            return False

        # Handle both engine.participants (new style) and engine.fighters (old style)
        if hasattr(self.engine, "participants"):
            fighters = [p.actor for p in self.engine.participants]
        elif hasattr(self.engine, "fighters"):
            fighters = self.engine.fighters
        else:
            return False

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

        if hasattr(self.engine, "participants"):
            current = {p.actor for p in self.engine.participants}
            
            # Add new fighters
            for actor in fighters - current:
                if hasattr(self.engine, "add_participant"):
                    self.engine.add_participant(actor)
            
            # Remove fighters no longer present in the room
            for actor in current - fighters:
                if hasattr(self.engine, "remove_participant"):
                    self.engine.remove_participant(actor)
            
            # Remove defeated combatants
            for actor in list(fighters):
                if _current_hp(actor) <= 0:
                    if hasattr(actor, "db"):
                        actor.db.in_combat = False
                    if hasattr(self.engine, "remove_participant"):
                        self.engine.remove_participant(actor)
        
        # Handle legacy fighter-based engines
        elif hasattr(self.engine, "fighters"):
            valid_fighters = []
            for fighter in list(self.engine.fighters):
                if not fighter:
                    continue

                if _current_hp(fighter) <= 0:
                    fighter.db.in_combat = False
                    continue

                if not getattr(fighter, "in_combat", False):
                    continue

                valid_fighters.append(fighter)

            self.engine.fighters = valid_fighters

            # Check for combat end
            if len(valid_fighters) <= 1:
                winner = valid_fighters[0] if valid_fighters else None
                self.end_combat(f"Combat ended - winner: {winner.key if winner else 'none'}")

    def process_round(self) -> None:
        """Process a single combat round for this instance."""
        if self.combat_ended:
            return

        self.round_number += 1
        self.last_round_time = time.time()

        try:
            self.sync_participants()

            if not self.has_active_fighters():
                return

            # Use engine's process_round if available
            if hasattr(self.engine, "process_round"):
                self.engine.process_round()
            else:
                self._manual_round_processing()

            self.sync_participants()

        except Exception as err:
            log_trace(f"Error in combat round processing: {err}")
            self.end_combat(f"Combat ended due to error: {err}")

    def _manual_round_processing(self) -> None:
        """Fallback round processing if engine doesn't have process_round."""
        fighters = getattr(self.engine, "fighters", [])
        
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

        fighters = getattr(self.engine, "fighters", [])
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
        CombatRoundManager.get().remove_combat(self.combat_id)

        # Clean up fighter states
        if self.engine:
            fighters = []
            if hasattr(self.engine, "participants"):
                fighters = [p.actor for p in self.engine.participants]
            elif hasattr(self.engine, "fighters"):
                fighters = self.engine.fighters

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
        self.running = False
        self.tick_delay = 2.0
        self._next_tick_scheduled = False
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

        inst = CombatInstance(combat_id, engine, set(fighters), round_time or self.tick_delay)
        self.combats[combat_id] = inst
        for fighter in fighters:
            self.combatant_to_combat[fighter] = combat_id

        inst.process_round()

        if not self.running:
            self.start_ticking()

        return inst

    def remove_combat(self, combat_id: int) -> None:
        """Remove combat ``combat_id`` from management."""
        inst = self.combats.pop(combat_id, None)
        if not inst:
            return
        for fighter in list(inst.combatants):
            self.combatant_to_combat.pop(fighter, None)
        if not self.combats:
            self.stop_ticking()

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
                if not self.running:
                    self.start_ticking()
                return inst
        return self.create_combat(combatants)

    def add_combatant_to_combat(
        self, combatant: object, instance: CombatInstance
    ) -> CombatInstance:
        """Add ``combatant`` to ``instance`` and return the combat instance."""

        if combatant in instance.combatants:
            return instance

        current = self.get_combatant_combat(combatant)
        if current:
            return current

        if instance.add_combatant(combatant):
            self.combatant_to_combat[combatant] = instance.combat_id

        if not self.running:
            self.start_ticking()

        return instance

    # ------------------------------------------------------------------
    # ticking logic
    # ------------------------------------------------------------------
    def start_ticking(self) -> None:
        if self.running:
            return
        self.running = True
        self._schedule_next_tick()

    def stop_ticking(self) -> None:
        self.running = False
        self._next_tick_scheduled = False

    def _schedule_next_tick(self) -> None:
        if not self.running or self._next_tick_scheduled:
            return
        self._next_tick_scheduled = True
        delay(self.tick_delay, self._tick)

    def _process_combats(self) -> List[int]:
        """Process all combats and return those to remove."""
        remove: List[int] = []

        for cid, inst in list(self.combats.items()):
            try:
                if not inst.is_valid():
                    remove.append(cid)
                    continue

                if not inst.has_active_fighters():
                    inst.end_combat("No active fighters remaining")
                    remove.append(cid)
                    continue

                inst.process_round()

                if inst.combat_ended:
                    remove.append(cid)

            except Exception as err:
                log_trace(f"Error processing combat instance: {err}")
                remove.append(cid)

        return remove

    def _cleanup_combats(self, combat_ids: List[int]) -> None:
        """Remove combats whose ids are in ``combat_ids``."""
        for cid in combat_ids:
            self.remove_combat(cid)

    def _tick(self) -> None:
        self._next_tick_scheduled = False
        if getattr(settings, "COMBAT_DEBUG_TICKS", False):
            log_trace("CombatRoundManager tick")
        if not self.running:
            return

        remove = self._process_combats()
        self._cleanup_combats(remove)

        # Schedule next tick if instances remain
        if self.combats and self.running:
            self._schedule_next_tick()

    # ------------------------------------------------------------------
    # debugging helpers
    # ------------------------------------------------------------------
    def get_combat_status(self) -> Dict:
        status = {
            "running": self.running,
            "total_instances": len(self.combats),
            "instances": [],
        }

        for inst in self.combats.values():
            # Get fighter count based on engine type
            fighter_count = 0
            if inst.engine:
                if hasattr(inst.engine, "participants"):
                    fighter_count = len(inst.engine.participants)
                elif hasattr(inst.engine, "fighters"):
                    fighter_count = len(inst.engine.fighters)

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
        self.stop_ticking()

    def debug_info(self) -> str:
        """Return formatted debug information about the combat manager."""
        status = self.get_combat_status()
        lines = [
            "Combat Manager Status:",
            f"  Running: {status['running']}",
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


def cleanup_legacy_room_combat() -> None:
    """Clean up any leftover room-based combat stored in `instances_by_room`."""
    mgr = CombatRoundManager._instance
    if not mgr:
        return
    # Older revisions stored combats in `instances_by_room`. Remove any that remain.
    if hasattr(mgr, "instances_by_room"):
        for inst in list(getattr(mgr, "instances_by_room", {}).values()):
            try:
                inst.end_combat("Migrated to ID-based combat")
            except Exception:
                pass
        mgr.instances_by_room.clear()
        if hasattr(mgr, "instances"):
            mgr.instances.clear()


cleanup_legacy_room_combat()
