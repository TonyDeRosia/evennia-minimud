"""Round and damage resolution."""

from __future__ import annotations

from typing import Dict, List
from evennia.utils import delay
from django.conf import settings

from combat.combatants import CombatParticipant, _current_hp
from combat.combat_utils import format_combat_message
from world.mechanics.death_handlers import get_handler, IDeathHandler
from world.mechanics import on_death_manager
from combat.engine.turn_manager import TurnManager
from combat.aggro_tracker import AggroTracker
from combat.damage_types import DamageType
from combat.events import combatant_defeated
from world.system import state_manager


class DamageProcessor:
    """Handle action execution and combat round flow."""

    def __init__(
        self,
        engine,
        turn_manager: TurnManager,
        aggro: AggroTracker,
        *,
        death_handler: IDeathHandler | None = None,
    ) -> None:
        self.engine = engine
        self.turn_manager = turn_manager
        self.aggro = aggro
        self.death_handler = death_handler or get_handler()
        self.round_output: List[str] = []
        self._message_buffers: Dict[object, List[str]] = {}

    def _buffer_message(self, participant: CombatParticipant, message: str) -> None:
        self._message_buffers.setdefault(participant.actor, []).append(message)

    def _flush_buffer(self, participant: CombatParticipant) -> None:
        msgs = self._message_buffers.pop(participant.actor, [])
        if msgs:
            self.round_output.extend(msgs)
            self.round_output.append("\n")

    # -------------------------------------------------------------
    # messaging helpers
    # -------------------------------------------------------------
    def dam_message(self, attacker, target, damage: int, *, crit: bool = False) -> None:
        if not attacker or not target or not attacker.location:
            return
        msg = format_combat_message(
            attacker, target, "hits", damage, crit=crit, adjective=True
        )
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
            chara.msg(f"You gain |Y{exp}|n experience points.")
        state_manager.gain_xp(chara, exp)

    def group_gain(self, members: List[object], exp: int) -> None:
        members = [m for m in members if m]
        if not members or not exp:
            return
        share = max(int(exp / len(members)), int(exp * 0.10))
        for member in members:
            if hasattr(member, "msg"):
                member.msg(f"You gain |Y{share}|n experience points.")
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

    def _apply_death_hooks(self, target, attacker) -> bool:
        """Run defeat/death hooks and return deletion status."""
        if hasattr(target, "on_exit_combat"):
            target.on_exit_combat()

        if hasattr(target, "at_defeat"):
            target.at_defeat(attacker)

        death_hook = getattr(target, "on_death", None)
        if callable(death_hook):
            death_hook(attacker)
        else:
            on_death_manager.handle_death(target, attacker, self.death_handler)

        deleted = getattr(target, "pk", None) is None
        if not deleted:
            self.update_pos(target)
        return deleted

    def _reassign_targets(self, inst, target, survivors, attacker) -> None:
        """Update combat targets for remaining fighters."""
        for combatant in survivors:
            if combatant is target:
                continue
            current = getattr(getattr(combatant, "db", None), "combat_target", None)
            has_hp = current and (
                hasattr(current, "hp")
                or getattr(getattr(current, "traits", None), "health", None) is not None
            )
            needs_new = current is target or not has_hp or (has_hp and _current_hp(current) <= 0)
            if needs_new:
                remaining = [c for c in survivors if c is not combatant]
                new_target = remaining[0] if remaining else None
                try:
                    combatant.db.combat_target = new_target
                except Exception:
                    pass
            if inst and combatant not in [p.actor for p in self.turn_manager.participants]:
                self.turn_manager.add_participant(combatant)

        if attacker and getattr(attacker, "db", None) is not None:
            try:
                others = [c for c in survivors if c is not attacker]
                attacker.db.combat_target = others[0] if others else None
            except Exception:
                pass

    def _pull_hostile_npcs(self, inst, target, prev_loc) -> None:
        """Add hostile bystanders to combat."""
        if not inst:
            return
        room = getattr(target, "location", None) or prev_loc
        if not room:
            return
        for obj in room.contents:
            has_hp = hasattr(obj, "hp") or getattr(getattr(obj, "traits", None), "health", None) is not None
            if not has_hp:
                continue
            if obj in inst.combatants:
                continue
            if _current_hp(obj) <= 0:
                continue
            t = getattr(getattr(obj, "db", None), "combat_target", None)
            if t in inst.combatants:
                inst.add_combatant(obj)
        inst.sync_participants()

    def _notify_allies(self, target, attacker) -> None:
        """Inform allies that a teammate has fallen."""
        for participant in list(self.turn_manager.participants):
            ally = participant.actor
            if ally is target:
                continue
            if ally.location == getattr(target, "location", None):
                hook = getattr(ally, "on_ally_down", None)
                if callable(hook):
                    hook(target, attacker)

    def handle_defeat(self, target, attacker) -> None:
        prev_loc = getattr(target, "location", None)
        from combat.round_manager import CombatRoundManager
        inst = CombatRoundManager.get().get_combatant_combat(target)

        deleted = self._apply_death_hooks(target, attacker)

        if inst and not deleted:
            inst.remove_combatant(target)

        if inst:
            survivors = [c for c in inst.combatants if _current_hp(c) > 0]
        else:
            survivors = [
                p.actor
                for p in self.turn_manager.participants
                if p.actor is not target and _current_hp(p.actor) > 0
            ]

        self._reassign_targets(inst, target, survivors, attacker)

        self._pull_hostile_npcs(inst, target, prev_loc)

        # Death notifications are handled by ``on_death`` on the defeated
        # character, so we avoid broadcasting here to prevent duplicates.
        self.turn_manager.remove_participant(target)

        self._notify_allies(target, attacker)

        combatant_defeated.send(
            sender=self.__class__,
            target=target,
            attacker=attacker,
            instance=inst,
        )

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
            hostiles = [
                p.actor
                for p in self.turn_manager.participants
                if p.actor is not actor
                and getattr(getattr(p.actor, "db", None), "combat_target", None) is actor
                and _current_hp(p.actor) > 0
            ]
            should_remove = (
                getattr(actor, "location", None) is None
                or hp <= 0
                or getattr(getattr(actor, "db", None), "is_dead", False)
                or (target is None and not participant.next_action and not hostiles)
            )
            if should_remove:
                if hp <= 0 and not getattr(getattr(actor, "db", None), "is_dead", False):
                    log = getattr(getattr(actor, "ndb", None), "damage_log", None) or {}
                    killer = max(log, key=log.get) if log else None
                    self.handle_defeat(actor, killer)

                self.turn_manager.remove_participant(actor)
                from combat.round_manager import CombatRoundManager
                inst = CombatRoundManager.get().get_combatant_combat(actor)
                if inst:
                    inst.remove_combatant(actor)

    # -------------------------------------------------------------
    # action / round execution
    # -------------------------------------------------------------
    def _execute_action(self, participant: CombatParticipant, action, damage_totals: Dict[object, int]) -> None:
        actor = participant.actor
        if getattr(getattr(actor, "db", None), "is_dead", False) or _current_hp(actor) <= 0:
            if action in participant.next_action:
                participant.next_action.remove(action)
            return
        target = getattr(action, "target", None)
        if target and (
            getattr(getattr(target, "db", None), "is_dead", False) or _current_hp(target) <= 0
        ):
            if action in participant.next_action:
                participant.next_action.remove(action)
            return
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

        from combat.action_resolvers import resolve_combat_result

        resolve_combat_result(self, participant, result, damage_totals)

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

    def _broadcast_round_output(self, room=None) -> None:
        if room is None:
            if self.turn_manager.participants:
                room = getattr(self.turn_manager.participants[0].actor, "location", None)

        if room:
            for line in self.round_output:
                room.msg_contents(line)
        else:
            for line in self.round_output:
                for participant in self.turn_manager.participants:
                    actor = participant.actor
                    if hasattr(actor, "msg"):
                        actor.msg(line)

    def process_round(self) -> None:
        self.turn_manager.start_round()
        self.round_output = []
        damage_totals: Dict[object, int] = {}

        actions = self.turn_manager.gather_actions()
        prev = None
        for _, _, _, participant, action in actions:
            if prev is not participant and prev is not None:
                self._flush_buffer(prev)
            prev = participant
            self._execute_action(participant, action, damage_totals)
        if prev is not None:
            self._flush_buffer(prev)

        room = None
        if self.turn_manager.participants:
            room = getattr(self.turn_manager.participants[0].actor, "location", None)

        self.cleanup_environment()
        self._summarize_damage(damage_totals)
        self.round_output.append("\n")
        self._broadcast_round_output(room)

        self.engine.round += 1
        if self.engine.round_time is not None and any(_current_hp(p.actor) > 0 for p in self.turn_manager.participants):
            delay(self.engine.round_time, self.engine.process_round)

