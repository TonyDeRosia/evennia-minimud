"""Status and combat state utilities."""

from dataclasses import dataclass
from typing import Callable, Dict, Optional


@dataclass
class CombatState:
    """Simple state effect that can stack."""

    key: str
    duration: int
    desc: str = ""
    max_stacks: int = 1
    diminish: float = 1.0
    stacks: int = 1
    on_apply: Optional[Callable[[object, "CombatState"], None]] = None
    on_expire: Optional[Callable[[object, "CombatState"], None]] = None
    on_tick: Optional[Callable[[object, "CombatState"], None]] = None


class StateManager:
    """Track active combat states on characters."""

    def __init__(self):
        self.states: Dict[object, Dict[str, CombatState]] = {}

    def add_state(self, obj: object, state: CombatState) -> None:
        """Add ``state`` to ``obj``.

        If the state already exists on the object it will stack and add
        duration using the state's ``diminish`` factor, up to ``max_stacks``.
        ``on_apply`` is only triggered the first time the state is added.
        """

        obj_states = self.states.setdefault(obj, {})
        current = obj_states.get(state.key)
        if current:
            if current.max_stacks is None or current.stacks < current.max_stacks:
                current.stacks += 1
            added = int(state.duration * (current.diminish ** (current.stacks - 1)))
            current.duration += added
        else:
            obj_states[state.key] = state
            if state.on_apply:
                state.on_apply(obj, state)

    def remove_state(self, obj: object, key: str) -> None:
        if obj in self.states and key in self.states[obj]:
            state = self.states[obj][key]
            if state.on_expire:
                state.on_expire(obj, state)
            del self.states[obj][key]

    def tick(self) -> None:
        """Advance all state timers and fire callbacks."""
        for obj, sts in list(self.states.items()):
            for key, state in list(sts.items()):
                if state.on_tick:
                    state.on_tick(obj, state)
                state.duration -= 1
                if state.duration <= 0:
                    if state.on_expire:
                        state.on_expire(obj, state)
                    del sts[key]
            if not sts:
                del self.states[obj]
