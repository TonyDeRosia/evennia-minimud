from __future__ import annotations

from typing import Type, Dict

__all__ = [
    "AI_REGISTRY",
    "BaseAI",
    "register_ai",
    "get_ai_class",
]

AI_REGISTRY: Dict[str, Type["BaseAI"]] = {}


class BaseAI:
    """Base class for simple AI behaviors."""

    key: str = ""

    def execute(self, npc):
        """Run one AI step for ``npc``."""
        raise NotImplementedError


def register_ai(key: str):
    """Class decorator for registering AI behaviors."""

    def decorator(cls: Type[BaseAI]):
        AI_REGISTRY[key] = cls
        cls.key = key
        return cls

    return decorator


def get_ai_class(key: str) -> Type[BaseAI] | None:
    """Return the registered AI class for ``key``."""
    return AI_REGISTRY.get(key)

from . import aggressive, defensive, wander, passive, scripted
