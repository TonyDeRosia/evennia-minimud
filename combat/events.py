"""Signals representing major combat events."""

from django.dispatch import Signal

#: emitted when a new combat instance starts
combat_started = Signal()

#: emitted after each combat round completes
round_processed = Signal()

#: emitted when a combatant is defeated and death logic runs
combatant_defeated = Signal()

#: emitted when a combat instance ends
combat_ended = Signal()

__all__ = [
    "combat_started",
    "round_processed",
    "combatant_defeated",
    "combat_ended",
]
