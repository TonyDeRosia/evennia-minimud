"""Status effect utilities for combat."""

from dataclasses import dataclass
from typing import Callable, Dict, Optional
from weakref import WeakKeyDictionary


@dataclass
class StatusEffect:
    """Simple status effect that can stack."""

    key: str
    duration: int
    desc: str = ""
    max_stacks: int = 1
    diminish: float = 1.0
    stacks: int = 1
    on_apply: Optional[Callable[[object, "StatusEffect"], None]] = None
    on_expire: Optional[Callable[[object, "StatusEffect"], None]] = None
    on_tick: Optional[Callable[[object, "StatusEffect"], None]] = None


class EffectManager:
    """Track active status effects on objects."""

    def __init__(self) -> None:
        self.effects: WeakKeyDictionary[object, Dict[str, StatusEffect]] = WeakKeyDictionary()

    def add_effect(self, obj: object, effect: StatusEffect) -> None:
        """Add ``effect`` to ``obj``.

        If the effect already exists on the object it will stack and add
        duration using the effect's ``diminish`` factor, up to ``max_stacks``.
        ``on_apply`` is only triggered the first time the effect is added.
        """

        obj_effects = self.effects.setdefault(obj, {})
        current = obj_effects.get(effect.key)
        if current:
            if current.max_stacks is None or current.stacks < current.max_stacks:
                current.stacks += 1
            added = int(effect.duration * (current.diminish ** (current.stacks - 1)))
            current.duration += added
        else:
            obj_effects[effect.key] = effect
            if effect.on_apply:
                effect.on_apply(obj, effect)

    def remove_effect(self, obj: object, key: str) -> None:
        if obj in self.effects and key in self.effects[obj]:
            effect = self.effects[obj][key]
            if effect.on_expire:
                effect.on_expire(obj, effect)
            del self.effects[obj][key]

    def tick(self) -> None:
        """Advance all effect timers and fire callbacks."""
        for obj, sts in list(self.effects.items()):
            for key, effect in list(sts.items()):
                if effect.on_tick:
                    effect.on_tick(obj, effect)
                effect.duration -= 1
                if effect.duration <= 0:
                    if effect.on_expire:
                        effect.on_expire(obj, effect)
                    del sts[key]
            if not sts:
                del self.effects[obj]
