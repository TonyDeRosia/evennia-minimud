"""Combat round management across all active rooms."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from evennia.utils import delay
from evennia.utils.logger import log_trace

from .combat_engine import CombatEngine


@dataclass
class CombatInstance:
    """Container for a combat engine tied to a room."""

    script: object
    engine: CombatEngine
    round_time: float = 2.0
    round_number: int = 0
    last_round_time: float = field(default_factory=time.time)
    combat_ended: bool = False

    def is_valid(self) -> bool:
        """Return ``True`` if the underlying script is still active."""
        return (
            self.script
            and getattr(self.script, "pk", None)
            and bool(getattr(self.script, "active", False))
            and not self.combat_ended
        )

    def has_active_fighters(self) -> bool:
        """Return ``True`` if at least two participants can still fight."""
        fighters = [p.actor for p in self.engine.participants]
        active = [f for f in fighters if getattr(f, "hp", 0) > 0]
        return len(active) >= 2

    def sync_participants(self) -> None:
        """Keep engine participants aligned with ``script.fighters``."""
        current = {p.actor for p in self.engine.participants}
        fighters = set(self.script.fighters)
        for actor in fighters - current:
            self.engine.add_participant(actor)
        for actor in current - fighters:
            self.engine.remove_participant(actor)
        # remove defeated combatants
        for actor in list(fighters):
            if getattr(actor, "hp", 0) <= 0:
                self.engine.remove_participant(actor)

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
            self.engine.process_round()
            self.sync_participants()
        except Exception as err:  # pragma: no cover - defensive
            log_trace(f"Error in combat round processing: {err}")
            self.end_combat(f"Combat ended due to error: {err}")

    def end_combat(self, reason: str = "") -> None:
        """Mark this instance as ended."""
        if self.combat_ended:
            return
        self.combat_ended = True
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
        for inst in self.instances:
            if inst.script is script:
                return inst
        engine = CombatEngine(script.fighters, round_time=None)
        inst = CombatInstance(script, engine, round_time or self.tick_delay)
        self.instances.append(inst)
        inst.process_round()
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
            except Exception as err:  # pragma: no cover - defensive
                log_trace(f"Error processing combat instance: {err}")
                remove.append(inst.script)
        for script in remove:
            self.remove_instance(script)
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
            status["instances"].append(
                {
                    "script": str(inst.script),
                    "round_number": inst.round_number,
                    "fighters": len(inst.engine.participants),
                    "valid": inst.is_valid(),
                    "has_active_fighters": inst.has_active_fighters(),
                    "ended": inst.combat_ended,
                }
            )
        return status

    def force_end_all_combat(self) -> None:
        for inst in list(self.instances):
            inst.end_combat("Force ended by admin")
        self.instances.clear()
        self.stop_ticking()

    def debug_info(self) -> str:
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
