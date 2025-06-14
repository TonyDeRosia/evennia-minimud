from __future__ import annotations

from importlib import import_module

from evennia.utils import logger

from combat.ai import BaseAI, register_ai

ALLOWED_CALLBACK_MODULES = ("scripts",)


def _import_ai_callback(path: str):
    """Import the AI callback if within allowed modules."""
    module, func = path.rsplit(".", 1)
    if not any(
        module == allowed or module.startswith(f"{allowed}.")
        for allowed in ALLOWED_CALLBACK_MODULES
    ):
        raise ImportError(f"Module '{module}' is not allowed")
    mod = import_module(module)
    return getattr(mod, func)


@register_ai("scripted")
class ScriptedAI(BaseAI):
    """Run a callback stored on ``npc.db.ai_script``."""

    def execute(self, npc):
        callback = npc.db.ai_script
        if not callback:
            return
        try:
            if callable(callback):
                callback(npc)
            elif isinstance(callback, str):
                try:
                    func = _import_ai_callback(callback)
                except Exception as err:
                    logger.log_err(f"Scripted AI import rejected on {npc}: {err}")
                    return
                func(npc)
        except Exception as err:  # pragma: no cover - log errors
            logger.log_err(f"Scripted AI error on {npc}: {err}")
