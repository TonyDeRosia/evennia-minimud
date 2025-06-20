"""Utilities for applying :class:`combat.combat_actions.CombatResult` objects."""

from __future__ import annotations

from typing import Dict

from .combatants import CombatParticipant, _current_hp
from .combat_utils import format_combat_message
from .damage_types import DamageType


def resolve_combat_result(processor, participant: CombatParticipant, result, damage_totals: Dict[object, int]) -> None:
    """Apply the effects of a :class:`~combat.combat_actions.CombatResult`."""

    actor = participant.actor
    target = result.target

    damage_done = 0
    msg = result.message

    if result.damage and target:
        dt = result.damage_type
        if isinstance(dt, str):
            try:
                dt = DamageType(dt)
            except ValueError:
                dt = None
        damage_done = processor.apply_damage(actor, target, result.damage, dt)
        if not msg:
            msg = format_combat_message(actor, target, "hits", damage_done)
        damage_totals[actor] = damage_totals.get(actor, 0) + damage_done

    if msg:
        processor._buffer_message(participant, msg)

    if target:
        processor.aggro.track(target, actor)
        if _current_hp(target) <= 0:
            defeated = target
            processor.handle_defeat(defeated, actor)
            for p in processor.turn_manager.participants:
                p.next_action = [
                    a
                    for a in p.next_action
                    if getattr(a, "target", None) is not defeated
                    and getattr(a, "actor", None) is not defeated
                ]


__all__ = ["resolve_combat_result"]

