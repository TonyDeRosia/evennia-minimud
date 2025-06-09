"""Core combat engine for round-based battles."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Iterable, Dict
import random
from evennia.utils import delay
from world.system import state_manager

from .combat_actions import Action, AttackAction, CombatResult


@dataclass
class CombatParticipant:
    """Representation of a combatant in the engine."""

    actor: object
    initiative: int = 0
    next_action: Optional[Action] = None


class CombatEngine:
    """Simple round-based combat engine."""

    def __init__(self, participants: Iterable[object] | None = None, round_time: int = 2, use_initiative: bool = True):
        self.participants: List[CombatParticipant] = []
        self.round = 0
        self.round_time = round_time
        self.use_initiative = use_initiative
        self.queue: List[CombatParticipant] = []
        self.aggro: Dict[object, Dict[object, int]] = {}
        if participants:
            for p in participants:
                self.add_participant(p)

    def add_participant(self, actor: object) -> None:
        """Add a combatant to this engine."""
        self.participants.append(CombatParticipant(actor=actor))
        if hasattr(actor, "on_enter_combat"):
            actor.on_enter_combat()

    def remove_participant(self, actor: object) -> None:
        """Remove ``actor`` from combat."""
        self.participants = [p for p in self.participants if p.actor is not actor]
        self.queue = [p for p in self.queue if p.actor is not actor]
        if hasattr(actor, "on_exit_combat"):
            actor.on_exit_combat()

    @property
    def turn_order(self) -> List[CombatParticipant]:
        """Return participants ordered by initiative descending."""
        return sorted(self.participants, key=lambda p: p.initiative, reverse=True)

    def queue_action(self, actor: object, action: Action) -> None:
        for participant in self.participants:
            if participant.actor is actor:
                participant.next_action = action
                break

    # -------------------------------------------------------------
    # Round Processing
    # -------------------------------------------------------------

    def start_round(self) -> None:
        """Prepare a new combat round."""
        self.queue = []
        for participant in self.participants:
            actor = participant.actor
            if hasattr(actor, "traits"):
                state_manager.apply_regen(actor)
                base = getattr(actor.traits.get("initiative"), "value", 0)
            else:
                base = getattr(actor, "initiative", 0)
            participant.initiative = base + random.randint(1, 20)
            self.queue.append(participant)
        if self.use_initiative:
            self.queue.sort(key=lambda p: p.initiative, reverse=True)

    def track_aggro(self, target, attacker) -> None:
        if not target or target is attacker:
            return
        data = self.aggro.setdefault(target, {})
        data[attacker] = data.get(attacker, 0) + 1

    def handle_defeat(self, target, attacker) -> None:
        if hasattr(target, "on_exit_combat"):
            target.on_exit_combat()
        if hasattr(target, "at_defeat"):
            target.at_defeat(attacker)
        self.remove_participant(target)

    def cleanup_environment(self) -> None:
        for participant in list(self.participants):
            actor = participant.actor
            if getattr(actor, "location", None) is None or getattr(actor, "hp", 1) <= 0:
                self.remove_participant(actor)

    def process_round(self) -> None:
        """Process a single combat round."""
        self.start_round()
        actions: list[tuple[int, int, CombatParticipant, Action]] = []
        for participant in list(self.queue):
            actor = participant.actor
            if not hasattr(actor, "hp") or actor.hp <= 0:
                continue
            action = participant.next_action or AttackAction(actor, None)
            actions.append(
                (
                    participant.initiative,
                    getattr(action, "priority", 0),
                    participant,
                    action,
                )
            )

        actions.sort(key=lambda t: (t[0], t[1]), reverse=True)

        for _, _, participant, action in actions:
            actor = participant.actor
            valid, err = action.validate()
            if not valid:
                result = CombatResult(actor=actor, target=actor, message=err)
            else:
                result = action.resolve()
            participant.next_action = None
            if actor.location:
                actor.location.msg_contents(result.message)
            if getattr(result.target, "hp", 1) <= 0:
                self.handle_defeat(result.target, actor)
            self.track_aggro(result.target, actor)
        self.cleanup_environment()
        self.round += 1
        delay(self.round_time, self.process_round)
