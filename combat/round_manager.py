from __future__ import annotations

from dataclasses import dataclass
from typing import List

from evennia.utils import delay

from .combat_engine import CombatEngine


@dataclass
class CombatInstance:
    """Wrapper for a combat engine tied to a room."""

    script: object
    engine: CombatEngine

    def sync_participants(self) -> None:
        """Synchronize engine participants with script fighters."""
        current = {p.actor for p in self.engine.participants}
        fighters = set(self.script.fighters)
        for actor in fighters - current:
            self.engine.add_participant(actor)
        for actor in current - fighters:
            self.engine.remove_participant(actor)


class CombatRoundManager:
    """Manage active combat instances across rooms."""

    _instance: "CombatRoundManager | None" = None

    def __init__(self):
        self.instances: List[CombatInstance] = []
        self.running = False

    @classmethod
    def get(cls) -> "CombatRoundManager":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def add_instance(self, script) -> CombatInstance:
        """Create or fetch an instance for ``script``."""
        for inst in self.instances:
            if inst.script is script:
                return inst
        engine = CombatEngine(script.fighters, round_time=None)
        inst = CombatInstance(script, engine)
        self.instances.append(inst)
        if not self.running:
            self.running = True
            self._schedule_tick()
        return inst

    def remove_instance(self, script) -> None:
        self.instances = [i for i in self.instances if i.script is not script]
        if not self.instances:
            self.running = False

    def _schedule_tick(self) -> None:
        delay(1, self.tick)

    def tick(self) -> None:
        for inst in list(self.instances):
            if not inst.script or not inst.script.active:
                self.remove_instance(inst.script)
                continue
            inst.sync_participants()
            inst.engine.process_round()
        if self.instances:
            self._schedule_tick()
        else:
            self.running = False
