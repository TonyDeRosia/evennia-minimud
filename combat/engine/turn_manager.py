"""Participant and turn order management."""

from __future__ import annotations

from typing import Iterable, List

from world.system import state_manager

from .common import CombatParticipant, _current_hp, HASTE_PER_EXTRA_ATTACK, MAX_ATTACKS_PER_ROUND
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
        if hasattr(actor, "db") and getattr(actor, "pk", None) is not None:
            actor.db.in_combat = True
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
        """Return a sorted list of actions for this round.

        Extra attacks granted by the ``haste`` stat are calculated once per
        participant and the total number of :class:`~combat.combat_actions.AttackAction`
        instances will never exceed ``MAX_ATTACKS_PER_ROUND``.
        """

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

            if participant.next_action:
                queued = list(participant.next_action)
            elif target:
                queued = [AttackAction(actor, target)]
            else:
                enemies = [p.actor for p in self.participants if p.actor is not actor and _current_hp(p.actor) > 0]
                if enemies:
                    queued = [AttackAction(actor, enemies[0])]
                else:
                    queued = []
                    if hasattr(actor, "msg"):
                        actor.msg("You hesitate, unsure of what to do.")

            attack_actions = []
            filtered: list[Action] = []
            for action in queued:
                if isinstance(action, AttackAction):
                    if len(attack_actions) < MAX_ATTACKS_PER_ROUND:
                        attack_actions.append(action)
                        filtered.append(action)
                else:
                    filtered.append(action)

            queued = filtered

            haste = state_manager.get_effective_stat(actor, "haste")
            extra = max(0, haste // HASTE_PER_EXTRA_ATTACK)
            extra = min(extra, MAX_ATTACKS_PER_ROUND - len(attack_actions))

            if extra and attack_actions:
                targets = [a.target for a in attack_actions]
                for i in range(extra):
                    queued.append(AttackAction(actor, targets[i % len(targets)]))

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

