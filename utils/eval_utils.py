from __future__ import annotations

"""Helper for safely evaluating condition strings."""

from typing import Any, Mapping
from evennia.utils import logger
from evennia.utils.utils import simple_eval

__all__ = ["eval_safe"]


def eval_safe(expr: str, context: Mapping[str, Any] | None = None) -> Any:
    """Safely evaluate a Python expression using ``simple_eval``.

    Args:
        expr: The expression to evaluate.
        context: Optional mapping of names to values available in the expression.

    Returns:
        The evaluated value or ``False`` if evaluation failed.
    """
    try:
        return simple_eval(expr, names=dict(context or {}))
    except Exception as err:  # pragma: no cover - log errors
        logger.log_err(f"Condition eval failed for '{expr}': {err}")
        return False
