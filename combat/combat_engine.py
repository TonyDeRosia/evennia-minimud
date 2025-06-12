"""Core combat engine for round-based battles."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Iterable, Dict
import random
from evennia.utils import delay
from world.system import state_manager

from .combat_actions import Action, AttackAction, CombatResult
from .damage_types import DamageType
from .combat_utils import (
    format_combat_message,
    calculate_initiative,
)
from world.combat import get_health_description


def _current_hp(obj):
    """Return current health of ``obj`` if available."""
    if hasattr(obj, "hp"):
        try:
            return obj.hp
        except Exception:
            pass
    hp_trait = getattr(getattr(obj, "traits", None), "health", None)
    if hp_trait is not None:
        return hp_trait.value
    return None


@dataclass
class CombatParticipant:
    """Representation of a combatant in the engine."""

    actor: object
    initiative: int = 0
    next_action: List[Action] = field(default_factory=list)


class CombatEngine:
    """Simple round-based combat engine."""

    def __init__(
        self,
        participants: Iterable[object] | None = None,
        round_time: int = 0,
        use_initiative: bool = True,
    ):
        """Create a new combat engine instance.

        Parameters
        ----------
        participants
            Optional iterable of initial combatants.
        round_time
            Delay between combat rounds in seconds. Defaults to ``0`` which
            immediately begins the next round after the previous one resolves.
        use_initiative
            If ``True`` initiative rolls determine action order.
        """
        self.participants: List[CombatParticipant] = []
        self.round = 0
        self.round_time = round_time
        self.use_initiative = use_initiative
        self.queue: List[CombatParticipant] = []
        self.aggro: Dict[object, Dict[object, int]] = {}
        self.round_output: List[str] = []
        if participants:
            for p in participants:
                self.add_participant(p)

    # -------------------------------------------------------------
    # Legacy helpers
    # -------------------------------------------------------------

    def update_pos(self, chara) -> None:
        """Update ``chara`` position tags based on remaining health.

        Parameters
        ----------
        chara
            Character being checked for status changes.

        Side Effects
        ------------
        Adds the ``unconscious`` and ``lying down`` status tags when
        ``chara`` has zero or less health.
        """
        hp = getattr(getattr(chara, "traits", None), "health", None)
        cur = hp.value if hp else getattr(chara, "hp", 1)
        if cur <= 0:
            if hasattr(chara, "tags"):
                chara.tags.add("unconscious", category="status")
                chara.tags.add("lying down", category="status")

    def change_alignment(self, attacker, victim) -> None:
        """Modify ``attacker`` alignment based on ``victim`` alignment.

        Parameters
        ----------
        attacker
            Character delivering the attack.
        victim
            Character being attacked.

        Side Effects
        ------------
        Adjusts ``attacker.db.alignment`` toward the opposite of
        ``victim`` and clamps the result between ``-1000`` and ``1000``.
        """
        if not attacker or not victim:
            return
        a_align = getattr(attacker.db, "alignment", None)
        v_align = getattr(victim.db, "alignment", None)
        if a_align is None or v_align is None:
            return
        attacker.db.alignment = max(-1000, min(1000, a_align - v_align))

    def solo_gain(self, chara, exp: int) -> None:
        """Award ``exp`` experience points directly to ``chara``.

        Parameters
        ----------
        chara
            Recipient of the experience points.
        exp
            Amount of experience awarded.

        Side Effects
        ------------
        Increases ``chara.db.exp`` and informs the character if possible.
        Triggers a level up check via :func:`state_manager.check_level_up`.
        """
        if not exp or not chara:
            return
        chara.db.exp = (chara.db.exp or 0) + exp
        if hasattr(chara, "msg"):
            chara.msg(f"You gain {exp} experience.")
        state_manager.check_level_up(chara)

    def group_gain(self, members: Iterable, exp: int) -> None:
        """Split ``exp`` experience between all ``members``.

        Parameters
        ----------
        members
            Iterable of characters receiving a share.
        exp
            Total experience value to divide amongst ``members``.

        Side Effects
        ------------
        Updates ``member.db.exp`` for each participant, sends a message if the
        member can be messaged and checks for level gains.
        """
        members = [m for m in members if m]
        if not members or not exp:
            return
        share = max(1, int(exp / len(members)))
        for member in members:
            member.db.exp = (member.db.exp or 0) + share
            if hasattr(member, "msg"):
                member.msg(f"You gain {share} experience.")
            state_manager.check_level_up(member)

    def dam_message(self, attacker, target, damage: int, *, crit: bool = False) -> None:
        """Announce that ``attacker`` dealt ``damage`` to ``target``.

        Parameters
        ----------
        attacker
            Character dealing the damage.
        target
            Character receiving the damage.
        damage
            Amount of damage dealt.
        crit
            Set to ``True`` if the hit was a critical strike.

        Side Effects
        ------------
        Broadcasts a formatted combat message to the attacker's location.
        """
        if not attacker or not target or not attacker.location:
            return
        msg = format_combat_message(attacker, target, "hits", damage, crit=crit)
        attacker.location.msg_contents(msg)

    def skill_message(self, actor, target, skill: str, success: bool = True) -> None:
        """Inform the room of a skill attempt.

        Parameters
        ----------
        actor
            Character attempting the skill.
        target
            Target of the skill, if any.
        skill
            Name of the skill used.
        success
            Whether the skill succeeded.

        Side Effects
        ------------
        Sends a descriptive message to ``actor.location`` if it exists.
        """
        if not actor or not actor.location:
            return
        if success:
            msg = f"{actor.key} uses {skill} on {getattr(target, 'key', 'nothing')}!"
        else:
            msg = f"{actor.key}'s {skill} fails to affect {getattr(target, 'key', 'anything')}!"
        actor.location.msg_contents(msg)

    def perform_violence(self) -> None:
        """Run a single combat round.

        This is a thin wrapper around :meth:`process_round` kept for
        backward compatibility.
        """
        self.process_round()

    def award_experience(self, attacker, victim) -> None:
        """Distribute experience for defeating ``victim``.

        Parameters
        ----------
        attacker
            Character credited with the kill.
        victim
            Character that was defeated.

        Side Effects
        ------------
        Awards experience either to ``attacker`` or split among all
        contributors tracked on ``victim``.
        """
        exp = getattr(victim.db, "exp_reward", 0) if hasattr(victim, "db") else 0
        if not exp:
            return
        contributors = list(self.aggro.get(victim, {}).keys()) or [attacker]
        if len(contributors) == 1:
            self.solo_gain(contributors[0], exp)
        else:
            self.group_gain(contributors, exp)

    def add_participant(self, actor: object) -> None:
        """Add a combatant to this engine.

        Parameters
        ----------
        actor
            Object representing the combatant to add.

        Side Effects
        ------------
        Appends a :class:`CombatParticipant` to :attr:`participants` and
        calls ``actor.on_enter_combat`` if present.
        """
        self.participants.append(CombatParticipant(actor=actor))
        if hasattr(actor, "ndb"):
            actor.ndb.combat_engine = self
        if hasattr(actor, "on_enter_combat"):
            actor.on_enter_combat()

    def remove_participant(self, actor: object) -> None:
        """Remove ``actor`` from combat.

        Parameters
        ----------
        actor
            Combatant to remove from this engine.

        Side Effects
        ------------
        Cleans ``actor`` from internal queues and invokes
        ``actor.on_exit_combat`` if available.
        """
        self.participants = [p for p in self.participants if p.actor is not actor]
        self.queue = [p for p in self.queue if p.actor is not actor]
        if hasattr(actor, "on_exit_combat"):
            actor.on_exit_combat()
        if hasattr(actor, "ndb") and hasattr(actor.ndb, "combat_engine"):
            del actor.ndb.combat_engine

    @property
    def turn_order(self) -> List[CombatParticipant]:
        """List combatants sorted by current initiative.

        Returns
        -------
        list[CombatParticipant]
            Participants ordered from highest to lowest initiative.
        """
        return sorted(self.participants, key=lambda p: p.initiative, reverse=True)

    def queue_action(self, actor: object, action: Action) -> None:
        """Set ``action`` as ``actor``'s next action.

        Parameters
        ----------
        actor
            The combatant performing the action.
        action
            The :class:`~combat.combat_actions.Action` instance to queue.

        Side Effects
        ------------
        Appends ``action`` to the ``next_action`` queue of the matching
        :class:`CombatParticipant`.
        """
        for participant in self.participants:
            if participant.actor is actor:
                participant.next_action.append(action)
                break

    # -------------------------------------------------------------
    # Round Processing
    # -------------------------------------------------------------

    def start_round(self) -> None:
        """Prepare initiative order and regenerate resources.

        Side Effects
        ------------
        Populates the internal action queue, applies regeneration and
        rolls initiative for each participant.
        """
        self.queue = []
        for participant in self.participants:
            actor = participant.actor
            if hasattr(actor, "traits"):
                state_manager.apply_regen(actor)
            participant.initiative = calculate_initiative(actor)
            self.queue.append(participant)
        if self.use_initiative:
            self.queue.sort(key=lambda p: p.initiative, reverse=True)

    def track_aggro(self, target, attacker) -> None:
        """Record threat generated by ``attacker`` on ``target``.

        Parameters
        ----------
        target
            Character becoming hostile toward ``attacker``.
        attacker
            Character generating threat.

        Side Effects
        ------------
        Updates an internal aggro table used when awarding experience.
        """
        if not target or target is attacker:
            return
        from world.system import state_manager

        data = self.aggro.setdefault(target, {})
        threat = 1 + state_manager.get_effective_stat(attacker, "threat")
        data[attacker] = data.get(attacker, 0) + threat

    def handle_defeat(self, target, attacker) -> None:
        """Handle ``target`` being reduced to zero health.

        Parameters
        ----------
        target
            The defeated character.
        attacker
            Character responsible for the defeat.

        Side Effects
        ------------
        Calls ``target.at_defeat`` if defined, removes the participant
        from combat and notifies allies in the same room.
        """
        if getattr(target, "pk", None) is None:
            # already cleaned up elsewhere
            self.remove_participant(target)
            return

        if hasattr(target, "on_exit_combat"):
            target.on_exit_combat()

        if hasattr(target, "at_defeat"):
            target.at_defeat(attacker)

        if getattr(target, "pk", None) is not None and hasattr(target, "on_death"):
            target.on_death(attacker)

        if getattr(target, "pk", None) is not None:
            self.update_pos(target)

        if attacker and attacker.location:
            attacker.location.msg_contents(
                f"{target.key} is defeated by {attacker.key}!"
            )

        self.remove_participant(target)
        for participant in list(self.participants):
            ally = participant.actor
            if ally is target:
                continue
            if ally.location == getattr(target, "location", None):
                hook = getattr(ally, "on_ally_down", None)
                if callable(hook):
                    hook(target, attacker)

    def apply_damage(
        self, attacker, target, amount: int, damage_type: DamageType | None
    ) -> int:
        """Apply ``amount`` of damage to ``target`` using its hooks.

        Parameters
        ----------
        attacker
            Character dealing the damage.
        target
            Character receiving the damage.
        amount
            Raw amount of damage attempted.
        damage_type
            Type of damage being inflicted.

        Returns
        -------
        int
            The actual damage dealt after hooks are processed.
        """

        if hasattr(target, "at_damage"):
            before = getattr(getattr(target, "traits", None), "health", None)
            if before:
                start = before.value
            else:
                start = getattr(target, "hp", 0)
            dealt = target.at_damage(attacker, amount, damage_type)
            if dealt is None:
                after = getattr(getattr(target, "traits", None), "health", None)
                if after:
                    dealt = start - after.value
                else:
                    dealt = start - getattr(target, "hp", start)
            return dealt
        elif hasattr(target, "hp"):
            target.hp = max(target.hp - amount, 0)
            return amount
        return 0

    def cleanup_environment(self) -> None:
        """Remove invalid participants from combat.

        Side Effects
        ------------
        Participants that have left the room or dropped to zero health are
        removed from the engine.
        """
        for participant in list(self.participants):
            actor = participant.actor
            hp = _current_hp(actor)
            if getattr(actor, "location", None) is None or (hp is not None and hp <= 0):
                self.remove_participant(actor)

    def process_round(self) -> None:
        """Execute all queued actions for the current round.

        Side Effects
        ------------
        Applies damage, sends combat messages, awards experience and
        schedules the next round using :func:`evennia.utils.delay`.
        """
        self.start_round()
        self.round_output = []
        damage_totals: Dict[object, int] = {}
        actions: list[tuple[int, int, CombatParticipant, Action]] = []
        for participant in list(self.queue):
            actor = participant.actor
            hp = _current_hp(actor)
            if hp is not None and hp <= 0:
                continue
            target = getattr(getattr(actor, "db", None), "combat_target", None)
            hook = getattr(actor, "at_combat_turn", None)
            if callable(hook):
                hook(target)

            queued = participant.next_action or [AttackAction(actor, target)]
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

        for _, _, _, participant, action in actions:
            actor = participant.actor
            valid, err = action.validate()
            if not valid:
                if hasattr(actor, "msg") and err:
                    actor.msg(err)
                participant.next_action = []
                continue
            result = action.resolve()

            participant.next_action = []

            damage_done = 0
            if result.damage and result.target:
                dt = result.damage_type
                if isinstance(dt, str):
                    try:
                        dt = DamageType(dt)
                    except ValueError:
                        dt = None
                damage_done = self.apply_damage(actor, result.target, result.damage, dt)
                if not result.message:
                    self.dam_message(actor, result.target, damage_done)
                damage_totals[actor] = damage_totals.get(actor, 0) + damage_done

            if result.target:
                cond = get_health_description(result.target)
                self.round_output.append(f"The {result.target.key} {cond}")

            if actor.location and result.message:
                actor.location.msg_contents(result.message)
            target_hp = _current_hp(result.target)
            if target_hp is not None and target_hp <= 0:
                self.handle_defeat(result.target, actor)
                self.award_experience(actor, result.target)
            self.track_aggro(result.target, actor)
        self.cleanup_environment()

        summary_lines = [
            f"{getattr(att, 'key', att)} dealt {dmg} damage."
            for att, dmg in damage_totals.items()
        ]
        if summary_lines:
            self.round_output.extend(summary_lines)

        if self.round_output:
            msg = "\n".join(self.round_output)
            room = None
            if self.participants:
                room = getattr(self.participants[0].actor, "location", None)
            if room:
                room.msg_contents(msg)
            else:
                for participant in self.participants:
                    actor = participant.actor
                    if hasattr(actor, "msg"):
                        actor.msg(msg)

        self.round += 1
        if not self.participants or self.round_time is None:
            return
        delay(self.round_time, self.process_round)
