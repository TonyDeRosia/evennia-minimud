"""Combat round management across all active rooms."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from evennia.utils import delay
from evennia.utils.logger import log_trace
from .combat_engine import _current_hp


@dataclass
class CombatInstance:
    """Container for a combat engine tied to a room."""

    script: object
    engine: object  # CombatEngine
    round_time: float = 2.0
    round_number: int = 0
    last_round_time: float = field(default_factory=time.time)
    combat_ended: bool = False

    def is_valid(self) -> bool:
        """Return ``True`` if the underlying script is still active."""
        return (
            self.script
            and hasattr(self.script, "pk")
            and self.script.pk
            and getattr(self.script, "active", False)
            and not self.combat_ended
        )

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
        """Keep engine participants aligned with script fighters and remove defeated combatants."""
        if not self.engine or not hasattr(self.script, "fighters"):
            self.end_combat("No fighters available")
            return

        # Handle modern participant-based engines
        if hasattr(self.engine, "participants"):
            current = {p.actor for p in self.engine.participants}
            fighters = set(self.script.fighters)

            # Add new fighters
            for actor in fighters - current:
                if hasattr(self.engine, "add_participant"):
                    self.engine.add_participant(actor)

            # Remove fighters no longer in script
            for actor in current - fighters:
                if hasattr(self.engine, "remove_participant"):
                    self.engine.remove_participant(actor)

            # Remove defeated combatants
            for actor in list(fighters):
                if _current_hp(actor) <= 0:
                    if hasattr(actor, "db") and getattr(actor, "pk", None) is not None:
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
                    if getattr(fighter, "pk", None) is not None:
                        fighter.db.in_combat = False
                    continue

                if not getattr(fighter, "in_combat", False):
                    continue

                valid_fighters.append(fighter)

            self.engine.fighters = valid_fighters

            # Check for combat end
            if len(valid_fighters) <= 1:
                winner = valid_fighters[0] if valid_fighters else None
                self.end_combat(
                    f"Combat ended - winner: {winner.key if winner else 'none'}"
                )

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

        # Clean up fighter states
        if self.engine:
            fighters = []
            if hasattr(self.engine, "participants"):
                fighters = [p.actor for p in self.engine.participants]
            elif hasattr(self.engine, "fighters"):
                fighters = self.engine.fighters

            for fighter in fighters:
                if (
                    fighter
                    and hasattr(fighter, "db")
                    and getattr(fighter, "pk", None) is not None
                ):
                    fighter.db.in_combat = False

        if reason:
            log_trace(f"Combat ended: {reason}")


class CombatRoundManager:
    """Manage all active combat instances."""

    _instance: Optional["CombatRoundManager"] = None

    def __init__(self) -> None:
        self.instances: List[CombatInstance] = []
        self.running = False
        self.tick_delay = 2.0
        self._next_tick_scheduled = False

    @classmethod
    def get(cls) -> "CombatRoundManager":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # instance management
    # ------------------------------------------------------------------
    def add_instance(
        self, script, round_time: Optional[float] = None
    ) -> CombatInstance:
        """Create or fetch a combat instance for ``script``."""
        # Check if instance already exists
        for inst in self.instances:
            if inst.script is script:
                return inst

        # Get fighters from script
        fighters = getattr(script, "fighters", [])
        if hasattr(script, "get_fighters"):
            fighters = script.get_fighters()

        # Create combat engine
        try:
            from .combat_engine import CombatEngine

            engine = CombatEngine(fighters, round_time=None)
        except ImportError:
            # Fallback for environments without the combat engine
            engine = None

        # Create instance
        inst = CombatInstance(script, engine, round_time or self.tick_delay)
        self.instances.append(inst)

        # Process initial round
        inst.process_round()

        # Start ticking if not already running
        if not self.running:
            self.start_ticking()

        return inst

    def remove_instance(self, script) -> None:
        """Remove ``script``'s instance from management."""
        self.instances = [i for i in self.instances if i.script is not script]
        if not self.instances:
            self.stop_ticking()

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

    def _tick(self) -> None:
        self._next_tick_scheduled = False
        if not self.running:
            return

        remove: List[object] = []

        for inst in list(self.instances):
            try:
                if not inst.is_valid():
                    remove.append(inst.script)
                    continue

                if not inst.has_active_fighters():
                    inst.end_combat("No active fighters remaining")
                    remove.append(inst.script)
                    continue

                inst.process_round()

                if inst.combat_ended:
                    remove.append(inst.script)

            except Exception as err:
                log_trace(f"Error processing combat instance: {err}")
                remove.append(inst.script)

        # Remove ended instances
        for script in remove:
            self.remove_instance(script)

        # Schedule next tick if instances remain
        if self.instances and self.running:
            self._schedule_next_tick()

    # ------------------------------------------------------------------
    # debugging helpers
    # ------------------------------------------------------------------
    def get_combat_status(self) -> Dict:
        status = {
            "running": self.running,
            "total_instances": len(self.instances),
            "instances": [],
        }

        for inst in self.instances:
            # Get fighter count based on engine type
            fighter_count = 0
            if inst.engine:
                if hasattr(inst.engine, "participants"):
                    fighter_count = len(inst.engine.participants)
                elif hasattr(inst.engine, "fighters"):
                    fighter_count = len(inst.engine.fighters)

            status["instances"].append(
                {
                    "script": str(inst.script),
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
        for inst in list(self.instances):
            inst.end_combat("Force ended by admin")
        self.instances.clear()
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
                    f"    Script: {inst['script']}",
                    f"    Round: {inst['round_number']}",
                    f"    Fighters: {inst['fighters']}",
                    f"    Valid: {inst['valid']}",
                    f"    Active: {inst['has_active_fighters']}",
                    f"    Ended: {inst['ended']}",
                    "",
                ]
            )

        return "\n".join(lines)
