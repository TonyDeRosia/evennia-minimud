"""Round and damage resolution."""

from __future__ import annotations

from typing import Dict, List
from evennia.utils import delay
from django.conf import settings

from .common import CombatParticipant, _current_hp
from ..combat_utils import format_combat_message
from .turn_manager import TurnManager
from .aggro_tracker import AggroTracker
from ..damage_types import DamageType
from world.system import state_manager


class DamageProcessor:
    """Handle action execution and combat round flow."""

    def __init__(self, engine, turn_manager: TurnManager, aggro: AggroTracker) -> None:
        self.engine = engine
        self.turn_manager = turn_manager
        self.aggro = aggro
        self.round_output: List[str] = []

    # -------------------------------------------------------------
    # messaging helpers
    # -------------------------------------------------------------
    def dam_message(self, attacker, target, damage: int, *, crit: bool = False) -> None:
        if not attacker or not target or not attacker.location:
            return
        msg = format_combat_message(attacker, target, "hits", damage, crit=crit)
        attacker.location.msg_contents(msg)

    def skill_message(self, actor, target, skill: str, success: bool = True) -> None:
        if not actor or not actor.location:
            return
        if success:
            msg = f"{actor.key} uses {skill} on {getattr(target, 'key', 'nothing')}!"
        else:
            msg = f"{actor.key}'s {skill} fails to affect {getattr(target, 'key', 'anything')}!"
        actor.location.msg_contents(msg)

    # -------------------------------------------------------------
    # defeat / damage helpers
    # -------------------------------------------------------------
    def update_pos(self, chara) -> None:
        hp = getattr(getattr(chara, "traits", None), "health", None)
        cur = hp.value if hp else getattr(chara, "hp", 1)
        if cur <= 0 and hasattr(chara, "tags"):
            chara.tags.add("unconscious", category="status")
            chara.tags.add("lying down", category="status")

    def change_alignment(self, attacker, victim) -> None:
        if not attacker or not victim:
            return
        a_align = getattr(attacker.db, "alignment", None)
        v_align = getattr(victim.db, "alignment", None)
        if a_align is None or v_align is None:
            return
        attacker.db.alignment = max(-1000, min(1000, a_align - v_align))

    def solo_gain(self, chara, exp: int) -> None:
        if not exp or not chara:
            return
        if hasattr(chara, "msg"):
            chara.msg(f"You gain {exp} experience.")
        state_manager.gain_xp(chara, exp)

    def group_gain(self, members: List[object], exp: int) -> None:
        members = [m for m in members if m]
        if not members or not exp:
            return
        share = max(int(exp / len(members)), int(exp * 0.10))
        for member in members:
            if hasattr(member, "msg"):
                member.msg(f"You gain {share} experience.")
            state_manager.gain_xp(member, share)

    def apply_damage(self, attacker, target, amount: int, damage_type: DamageType | None) -> int:
        if hasattr(target, "at_damage"):
            before = getattr(getattr(target, "traits", None), "health", None)
            start = before.value if before else getattr(target, "hp", 0)
            dealt = target.at_damage(attacker, amount, damage_type)
            if dealt is None:
                after = getattr(getattr(target, "traits", None), "health", None)
                dealt = start - (after.value if after else getattr(target, "hp", start))
            return dealt
        elif hasattr(target, "hp"):
            target.hp = max(target.hp - amount, 0)
            return amount
        return 0

    def handle_defeat(self, target, attacker) -> None:
        if getattr(target, "pk", None) is None:
            self.turn_manager.remove_participant(target)
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
            attacker.location.msg_contents(f"{target.key} is defeated by {attacker.key}!")
        if attacker and getattr(attacker, "db", None) is not None:
            attacker.db.combat_target = None

        self.turn_manager.remove_participant(target)
        for participant in list(self.turn_manager.participants):
            ally = participant.actor
            if ally is target:
                continue
            if ally.location == getattr(target, "location", None):
                hook = getattr(ally, "on_ally_down", None)
                if callable(hook):
                    hook(target, attacker)

    def cleanup_environment(self) -> None:
        """Remove combatants that are no longer able or willing to fight.

        Participants are removed if they:
        - have left the room,
        - have no remaining health, or
        - have cleared their ``db.combat_target`` and have nothing queued.

        Clearing the target is treated as an explicit request to disengage, so
        pending actions keep the fighter in combat until resolved.
        """
        for participant in list(self.turn_manager.participants):
            actor = participant.actor
            hp = _current_hp(actor)
            target = getattr(getattr(actor, "db", None), "combat_target", None)
            should_remove = (
                getattr(actor, "location", None) is None
                or hp <= 0
                or (target is None and not participant.next_action)
            )
            if should_remove:
                self.turn_manager.remove_participant(actor)

    # -------------------------------------------------------------
    # action / round execution
    # -------------------------------------------------------------
    def _execute_action(self, participant: CombatParticipant, action, damage_totals: Dict[object, int]) -> None:
        actor = participant.actor
        valid, err = action.validate()
        if not valid:
            if hasattr(actor, "msg") and err:
                actor.msg(err)
            if action in participant.next_action:
                participant.next_action.remove(action)
            return

        result = action.resolve()

        if action in participant.next_action:
            participant.next_action.remove(action)

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

        if actor.location and result.message:
            actor.location.msg_contents(result.message)

        if result.target:
            self.aggro.track(result.target, actor)
            if _current_hp(result.target) <= 0:
                self.handle_defeat(result.target, actor)

    def _summarize_damage(self, damage_totals: Dict[object, int]) -> None:
        if not getattr(settings, "COMBAT_DEBUG_SUMMARY", False):
            return

        summary_lines = [
            f"{getattr(att, 'key', att)} dealt {dmg} damage."
            for att, dmg in damage_totals.items()
            if dmg > 0
        ]
        if summary_lines:
            self.round_output.extend(summary_lines)

    def _broadcast_round_output(self) -> None:
        if not self.round_output:
            return
        msg = "\n".join(self.round_output)
        room = None
        if self.turn_manager.participants:
            room = getattr(self.turn_manager.participants[0].actor, "location", None)
        if room:
            room.msg_contents(msg)
        else:
            for participant in self.turn_manager.participants:
                actor = participant.actor
                if hasattr(actor, "msg"):
                    actor.msg(msg)

    def process_round(self) -> None:
        self.turn_manager.start_round()
        self.round_output = []
        damage_totals: Dict[object, int] = {}

        actions = self.turn_manager.gather_actions()
        for _, _, _, participant, action in actions:
            self._execute_action(participant, action, damage_totals)

        self.cleanup_environment()
        self._summarize_damage(damage_totals)
        self._broadcast_round_output()

        self.engine.round += 1
        if self.engine.round_time is not None and any(_current_hp(p.actor) > 0 for p in self.turn_manager.participants):
            delay(self.engine.round_time, self.engine.process_round)

