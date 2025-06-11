"""Core combat engine for round-based battles."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Iterable, Dict
import random
from evennia.utils import delay
from world.system import state_manager

from .combat_actions import Action, AttackAction, CombatResult
from .damage_types import DamageType
from .combat_utils import format_combat_message


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

    # -------------------------------------------------------------
    # Legacy helpers
    # -------------------------------------------------------------

    def update_pos(self, chara) -> None:
        """Update position tags based on current health."""
        hp = getattr(getattr(chara, "traits", None), "health", None)
        cur = hp.value if hp else getattr(chara, "hp", 1)
        if cur <= 0:
            if hasattr(chara, "tags"):
                chara.tags.add("unconscious", category="status")
                chara.tags.add("lying down", category="status")

    def change_alignment(self, attacker, victim) -> None:
        """Modify ``attacker`` alignment based on ``victim``."""
        if not attacker or not victim:
            return
        a_align = getattr(attacker.db, "alignment", None)
        v_align = getattr(victim.db, "alignment", None)
        if a_align is None or v_align is None:
            return
        attacker.db.alignment = max(-1000, min(1000, a_align - v_align))

    def solo_gain(self, chara, exp: int) -> None:
        """Award ``exp`` to ``chara``."""
        if not exp or not chara:
            return
        chara.db.exp = (chara.db.exp or 0) + exp
        if hasattr(chara, "msg"):
            chara.msg(f"You gain {exp} experience.")
        state_manager.check_level_up(chara)

    def group_gain(self, members: Iterable, exp: int) -> None:
        """Split ``exp`` between ``members``."""
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
        """Announce dealt damage to the room."""
        if not attacker or not target or not attacker.location:
            return
        msg = format_combat_message(attacker, target, "hits", damage, crit=crit)
        attacker.location.msg_contents(msg)

    def skill_message(self, actor, target, skill: str, success: bool = True) -> None:
        """Announce the result of a skill use."""
        if not actor or not actor.location:
            return
        if success:
            msg = f"{actor.key} uses {skill} on {getattr(target, 'key', 'nothing')}!"
        else:
            msg = f"{actor.key}'s {skill} fails to affect {getattr(target, 'key', 'anything')}!"
        actor.location.msg_contents(msg)

    def perform_violence(self) -> None:
        """Alias for :meth:`process_round`."""
        self.process_round()

    def award_experience(self, attacker, victim) -> None:
        """Distribute experience for defeating ``victim``."""
        exp = getattr(victim.db, "exp_reward", 0) if hasattr(victim, "db") else 0
        if not exp:
            return
        contributors = list(self.aggro.get(victim, {}).keys()) or [attacker]
        if len(contributors) == 1:
            self.solo_gain(contributors[0], exp)
        else:
            self.group_gain(contributors, exp)

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
        from world.system import state_manager

        data = self.aggro.setdefault(target, {})
        threat = 1 + state_manager.get_effective_stat(attacker, "threat")
        data[attacker] = data.get(attacker, 0) + threat

    def handle_defeat(self, target, attacker) -> None:
        if hasattr(target, "on_exit_combat"):
            target.on_exit_combat()
        if hasattr(target, "at_defeat"):
            target.at_defeat(attacker)
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

    def apply_damage(self, attacker, target, amount: int, damage_type: DamageType | None) -> int:
        """Apply ``amount`` of damage to ``target`` using its hooks."""

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

            damage_done = 0
            if result.damage and result.target:
                dt = result.damage_type
                if isinstance(dt, str):
                    try:
                        dt = DamageType(dt)
                    except ValueError:
                        dt = None
                damage_done = self.apply_damage(actor, result.target, result.damage, dt)
                self.dam_message(actor, result.target, damage_done)
            
            if actor.location and not result.damage:
                actor.location.msg_contents(result.message)
            if getattr(result.target, "hp", 1) <= 0:
                self.handle_defeat(result.target, actor)
                self.award_experience(actor, result.target)
            self.track_aggro(result.target, actor)
        self.cleanup_environment()
        self.round += 1
        delay(self.round_time, self.process_round)
