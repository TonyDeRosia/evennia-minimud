"""Thin orchestrator for combat logic."""

from __future__ import annotations

from typing import Iterable

from .turn_manager import TurnManager
from .aggro_tracker import AggroTracker
from .damage_processor import DamageProcessor


class CombatEngine:
    """Manage combat by delegating to helper classes."""

    def __init__(self, participants: Iterable[object] | None = None, round_time: int = 0, use_initiative: bool = True) -> None:
        self.round = 0
        self.round_time = round_time
        self.turn_manager = TurnManager(self, participants, use_initiative=use_initiative)
        self.aggro_tracker = AggroTracker()
        self.processor = DamageProcessor(self, self.turn_manager, self.aggro_tracker)

    # -------------------------------------------------------------
    # delegate helpers
    # -------------------------------------------------------------
    @property
    def participants(self):
        return self.turn_manager.participants

    @property
    def aggro(self):
        return self.aggro_tracker.table

    def add_participant(self, actor: object) -> None:
        self.turn_manager.add_participant(actor)

    def remove_participant(self, actor: object) -> None:
        self.turn_manager.remove_participant(actor)

    def queue_action(self, actor: object, action) -> None:
        self.turn_manager.queue_action(actor, action)

    def start_round(self) -> None:
        self.turn_manager.start_round()

    def process_round(self) -> None:
        self.processor.process_round()

    # Convenience wrappers for processor functionality
    def dam_message(self, *args, **kwargs):
        self.processor.dam_message(*args, **kwargs)

    def skill_message(self, *args, **kwargs):
        self.processor.skill_message(*args, **kwargs)

    def apply_damage(self, *args, **kwargs):
        return self.processor.apply_damage(*args, **kwargs)

    def handle_defeat(self, *args, **kwargs):
        self.processor.handle_defeat(*args, **kwargs)

    def award_experience(self, attacker, victim) -> None:
        active = [p.actor for p in self.turn_manager.participants]
        self.aggro_tracker.award_experience(attacker, victim, active)

