"""Combat AI helpers."""

from .ai_controller import Behavior, run_behaviors
from .npc_logic import npc_take_turn

__all__ = ["Behavior", "run_behaviors", "npc_take_turn"]
