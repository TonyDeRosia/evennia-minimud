"""Participant and turn order management."""

from __future__ import annotations

from typing import Iterable, List

from world.system import state_manager

from .common import HASTE_PER_EXTRA_ATTACK, MAX_ATTACKS_PER_ROUND
from ..combatants import CombatParticipant, _current_hp
from ..combat_actions import AttackAction, Action
from ..combat_utils import calculate_initiative


class TurnManager:
    """Track combat participants and build the action queue."""

    def __init__(self, engine, participants: Iterable[object] | None = None, *, use_initiative: bool = True) -> None:
        self.engine = engine
        self.use_initiative = use_initiative
        self.participants: List[CombatParticipant] = []
        self.queue: List[CombatParticipant] = []
        if participants:
            for p in participants:
                self.add_participant(p)

    # -------------------------------------------------------------
    # participant management
    # -------------------------------------------------------------
    def add_participant(self, actor: object) -> None:
        # Always mark the actor as being in combat **before** it is queued. This
        # ensures that any hooks triggered during `on_enter_combat` or later
        # phases can rely on this flag being set.
        if hasattr(actor, "db") and getattr(actor, "pk", None) is not None:
            actor.db.in_combat = True
        else:
            setattr(actor, "in_combat", True)

        self.participants.append(CombatParticipant(actor=actor))
        if hasattr(actor, "ndb"):
            actor.ndb.combat_engine = self.engine
        if hasattr(actor, "on_enter_combat"):
            actor.on_enter_combat()

    def remove_participant(self, actor: object) -> None:
        self.participants = [p for p in self.participants if p.actor is not actor]
        self.queue = [p for p in self.queue if p.actor is not actor]

        if hasattr(actor, "db") and getattr(actor, "pk", None) is not None:
            actor.db.in_combat = False
            actor.db.combat_target = None
        else:
            setattr(actor, "in_combat", False)
            setattr(actor, "combat_target", None)
        if hasattr(actor, "on_exit_combat"):
            actor.on_exit_combat()
        if hasattr(actor, "ndb") and hasattr(actor.ndb, "combat_engine"):
            del actor.ndb.combat_engine

    @property
    def turn_order(self) -> List[CombatParticipant]:
        return sorted(self.participants, key=lambda p: p.initiative, reverse=True)

    def queue_action(self, actor: object, action: Action) -> None:
        for participant in self.participants:
            if participant.actor is actor:
                participant.next_action.append(action)
                break

    # -------------------------------------------------------------
    # round setup
    # -------------------------------------------------------------
    def start_round(self) -> None:
        self.queue = []
        for participant in self.participants:
            actor = participant.actor
            if hasattr(actor, "traits"):
                state_manager.apply_regen(actor)
            participant.initiative = calculate_initiative(actor)
            self.queue.append(participant)
        if self.use_initiative:
            self.queue.sort(key=lambda p: p.initiative, reverse=True)

    # -------------------------------------------------------------
    # action gathering
    # -------------------------------------------------------------
    def gather_actions(self) -> list[tuple[int, int, int, CombatParticipant, Action]]:
        actions: list[tuple[int, int, int, CombatParticipant, Action]] = []
        for participant in list(self.queue):
            actor = participant.actor
            hp = _current_hp(actor)
            if hp <= 0:
                continue
            target = getattr(getattr(actor, "db", None), "combat_target", None)
            hook = getattr(actor, "at_combat_turn", None)
            if callable(hook):
                hook(target)

            # default action resolution
            if participant.next_action:
                queued = list(participant.next_action)
            else:
                if target and _current_hp(target) > 0:
                    queued = [AttackAction(actor, target)]
                else:
                    enemy = next(
                        (
                            p.actor
                            for p in self.participants
                            if p.actor is not actor and _current_hp(p.actor) > 0
                        ),
                        None,
                    )
                    if enemy:
                        queued = [AttackAction(actor, enemy)]
                    else:
                        queued = []
                        living = any(
                            _current_hp(p.actor) > 0 and p.actor is not actor
                            for p in self.participants
                        )
                        if living and hasattr(actor, "msg"):
                            actor.msg("You hesitate, unsure of what to do.")

            haste = state_manager.get_effective_stat(actor, "haste")
            extra = max(0, haste // HASTE_PER_EXTRA_ATTACK)
            extra = min(extra, MAX_ATTACKS_PER_ROUND - 1)
            if extra and queued:
                extras: list[Action] = []
                for action in queued:
                    if isinstance(action, AttackAction):
                        for _ in range(extra):
                            extras.append(AttackAction(actor, action.target))
                queued.extend(extras)

            for idx, action in enumerate(queued):
                actions.append(
                    (
                        participant.initiative,
                        getattr(action, "priority", 0),
                        -idx,
                        participant,
                        action,
                    )
                )

        actions.sort(key=lambda t: (t[0], t[1], t[2]), reverse=True)
        return actions

