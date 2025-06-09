"""Status and combat state utilities."""

from dataclasses import dataclass
from typing import Dict


@dataclass
class CombatState:
    """Simple state effect."""

    key: str
    duration: int
    desc: str = ""


class StateManager:
    """Track active combat states on characters."""

    def __init__(self):
        self.states: Dict[object, Dict[str, CombatState]] = {}

    def add_state(self, obj: object, state: CombatState) -> None:
        self.states.setdefault(obj, {})[state.key] = state

    def remove_state(self, obj: object, key: str) -> None:
        if obj in self.states and key in self.states[obj]:
            del self.states[obj][key]

    def tick(self) -> None:
        for obj, sts in list(self.states.items()):
            for key, state in list(sts.items()):
                state.duration -= 1
                if state.duration <= 0:
                    del sts[key]
            if not sts:
                del self.states[obj]
