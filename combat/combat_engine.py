"""Core combat engine for round-based battles."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Iterable
from evennia.utils import delay

from .combat_actions import Action, AttackAction


@dataclass
class CombatParticipant:
    """Representation of a combatant in the engine."""

    actor: object
    initiative: int = 0
    next_action: Optional[Action] = None


class CombatEngine:
    """Simple round-based combat engine."""

    def __init__(self, participants: Iterable[object] | None = None, round_time: int = 2):
        self.participants: List[CombatParticipant] = []
        self.round = 0
        self.round_time = round_time
        if participants:
            for p in participants:
                self.add_participant(p)

    def add_participant(self, actor: object) -> None:
        self.participants.append(CombatParticipant(actor=actor))

    @property
    def turn_order(self) -> List[CombatParticipant]:
        """Return participants ordered by initiative descending."""
        return sorted(self.participants, key=lambda p: p.initiative, reverse=True)

    def queue_action(self, actor: object, action: Action) -> None:
        for participant in self.participants:
            if participant.actor is actor:
                participant.next_action = action
                break

    def process_round(self) -> None:
        """Process a single combat round."""
        for participant in self.turn_order:
            if not hasattr(participant.actor, "hp"):
                continue
            if participant.actor.hp <= 0:
                continue
            action = participant.next_action or AttackAction(participant.actor, None)
            result = action.resolve()
            participant.next_action = None
            if participant.actor.location:
                participant.actor.location.msg_contents(result.message)
            if getattr(result.target, "hp", 1) <= 0:
                if hasattr(result.target, "at_defeat"):
                    result.target.at_defeat(participant.actor)
        self.round += 1
        delay(self.round_time, self.process_round)
