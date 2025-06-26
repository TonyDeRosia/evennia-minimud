from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Iterable

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - imported for type checking
    from ..engine import CombatEngine


@dataclass(order=True)
class Behavior:
    """A prioritized behavior condition/action pair."""

    priority: int
    check: Callable[[CombatEngine | None, object, object], bool] = field(compare=False)
    act: Callable[[CombatEngine | None, object, object], None] = field(compare=False)


def run_behaviors(
    engine: CombatEngine | None,
    npc: object,
    target: object,
    behaviors: Iterable[Behavior],
) -> None:
    """Execute the first valid behavior from ``behaviors``."""

    for beh in sorted(list(behaviors), reverse=True):
        if beh.check(engine, npc, target):
            beh.act(engine, npc, target)
            break
