"""Combat Round Manager - Handles automatic combat rounds across all rooms"""

from typing import List, Dict, Optional
from evennia.utils import delay
from evennia.utils.logger import log_trace
import time


class CombatInstance:
    """Represents a single combat encounter in a specific location."""

    def __init__(self, script, engine, round_time: float = 2.0):
        self.script = script
        self.engine = engine
        self.round_time = round_time
        self.round_number = 0
        self.last_round_time = time.time()
        self.combat_ended = False

    def is_valid(self) -> bool:
        """Check if this combat instance is still valid."""
        return (
            self.script
            and hasattr(self.script, "pk")
            and self.script.pk
            and getattr(self.script, "active", False)
            and not self.combat_ended
        )

    def has_active_fighters(self) -> bool:
        """Check if there are still fighters capable of combat."""
        if not self.engine or not hasattr(self.engine, "fighters"):
            return False

        active_fighters = []
        for fighter in self.engine.fighters:
            if not fighter or not hasattr(fighter, "db"):
                continue
            if getattr(fighter.db, "hp", 0) > 0 and getattr(fighter.db, "in_combat", False):
                active_fighters.append(fighter)

        return len(active_fighters) >= 2

    def sync_participants(self):
        """Remove dead/fled participants and check for combat end."""
        if not self.engine or not hasattr(self.engine, "fighters"):
            self.end_combat("No fighters available")
            return

        valid_fighters = []
        for fighter in list(self.engine.fighters):
            if not fighter or not hasattr(fighter, "db"):
                continue

            if getattr(fighter.db, "hp", 0) <= 0:
                fighter.db.in_combat = False
                continue

            if not getattr(fighter.db, "in_combat", False):
                continue

            valid_fighters.append(fighter)

        self.engine.fighters = valid_fighters

        if len(valid_fighters) <= 1:
            winner = valid_fighters[0] if valid_fighters else None
            self.end_combat(f"Combat ended - winner: {winner.key if winner else 'none'}")

    def process_round(self):
        """Process a single combat round."""
        if self.combat_ended:
            return

        self.round_number += 1
        self.last_round_time = time.time()

        try:
            self.sync_participants()

            if not self.has_active_fighters():
                return

            if hasattr(self.engine, "process_round"):
                self.engine.process_round()
            else:
                self._manual_round_processing()

            self.sync_participants()

        except Exception as e:
            log_trace(f"Error in combat round processing: {e}")
            self.end_combat(f"Combat ended due to error: {e}")

    def _manual_round_processing(self):
        """Fallback round processing if engine doesn't have process_round."""
        for fighter in list(self.engine.fighters):
            if not fighter or getattr(fighter.db, "hp", 0) <= 0:
                continue

            if not getattr(fighter.db, "in_combat", False):
                continue

            if not hasattr(fighter, "has_account") or not fighter.has_account:
                self._npc_auto_attack(fighter)

    def _npc_auto_attack(self, npc):
        """Handle NPC automatic attacks."""
        if not npc or not hasattr(npc, "location"):
            return

        targets = []
        for fighter in self.engine.fighters:
            if (
                fighter != npc
                and hasattr(fighter, "has_account")
                and fighter.has_account
                and getattr(fighter.db, "hp", 0) > 0
                and getattr(fighter.db, "in_combat", False)
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

    def end_combat(self, reason: str = ""):
        """End this combat instance."""
        if self.combat_ended:
            return

        self.combat_ended = True

        if self.engine and hasattr(self.engine, "fighters"):
            for fighter in self.engine.fighters:
                if fighter and hasattr(fighter, "db"):
                    fighter.db.in_combat = False

        if reason:
            log_trace(f"Combat ended: {reason}")


class CombatRoundManager:
    """Manage active combat instances across all rooms."""

    _instance: Optional["CombatRoundManager"] = None

    def __init__(self):
        self.instances: List[CombatInstance] = []
        self.running = False
        self.tick_delay = 2.0
        self._next_tick_scheduled = False

    @classmethod
    def get(cls) -> "CombatRoundManager":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def add_instance(self, script, round_time: Optional[float] = None) -> CombatInstance:
        for inst in self.instances:
            if inst.script is script:
                return inst

        fighters = getattr(script, "fighters", [])
        if hasattr(script, "get_fighters"):
            fighters = script.get_fighters()

        from .combat_engine import CombatEngine

        engine = CombatEngine(fighters, round_time=None)
        inst = CombatInstance(script, engine, round_time or self.tick_delay)
        self.instances.append(inst)

        inst.process_round()

        if not self.running:
            self.start_ticking()

        return inst

    def remove_instance(self, script) -> None:
        self.instances = [i for i in self.instances if i.script is not script]
        if not self.instances:
            self.stop_ticking()

    def start_ticking(self):
        if self.running:
            return

        self.running = True
        self._schedule_next_tick()

    def stop_ticking(self):
        self.running = False
        self._next_tick_scheduled = False

    def _schedule_next_tick(self):
        if not self.running or self._next_tick_scheduled:
            return

        self._next_tick_scheduled = True
        delay(self.tick_delay, self._tick)

    def _tick(self):
        self._next_tick_scheduled = False

        if not self.running:
            return

        instances_to_remove = []

        for inst in list(self.instances):
            try:
                if not inst.is_valid():
                    instances_to_remove.append(inst.script)
                    continue

                if not inst.has_active_fighters():
                    inst.end_combat("No active fighters remaining")
                    instances_to_remove.append(inst.script)
                    continue

                inst.process_round()

                if inst.combat_ended:
                    instances_to_remove.append(inst.script)

            except Exception as e:
                log_trace(f"Error processing combat instance: {e}")
                instances_to_remove.append(inst.script)

        for script in instances_to_remove:
            self.remove_instance(script)

        if self.instances and self.running:
            self._schedule_next_tick()

    def get_combat_status(self) -> Dict:
        status = {"running": self.running, "total_instances": len(self.instances), "instances": []}

        for inst in self.instances:
            inst_status = {
                "script": str(inst.script),
                "round_number": inst.round_number,
                "fighters": len(inst.engine.fighters) if inst.engine else 0,
                "valid": inst.is_valid(),
                "has_active_fighters": inst.has_active_fighters(),
                "ended": inst.combat_ended,
            }
            status["instances"].append(inst_status)

        return status

    def force_end_all_combat(self):
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
                    f"  Instance {i+1}:",
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
