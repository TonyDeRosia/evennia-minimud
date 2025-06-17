"""Utilities for working with Evennia scripts."""

from typing import Iterable, List

from evennia.utils import logger
from evennia.scripts.models import ScriptDB


def resume_paused_scripts(keys: Iterable[str] | None = None,
                           paths: Iterable[str] | None = None,
                           log: bool = True) -> List[ScriptDB]:
    """Resume paused scripts.

    Parameters
    ----------
    keys
        Optional iterable of script keys to resume. If omitted, all
        paused scripts are considered.
    paths
        Optional iterable of typeclass paths to resume. Scripts must
        match either a key in ``keys`` or a path in ``paths`` when
        these are supplied.
    log
        If ``True``, log each resumed script to the Evennia logger.

    Returns
    -------
    list
        The resumed ``ScriptDB`` instances.
    """

    keyset = set(keys or [])
    pathset = set(paths or [])

    resumed: List[ScriptDB] = []
    for script in ScriptDB.objects.filter(db_is_active=True):
        if not getattr(script.db, "_paused_time", None):
            continue
        if keyset or pathset:
            if not ((script.key in keyset) or (script.typeclass_path in pathset)):
                continue
        if getattr(script.db, "manual_pause", False):
            continue
        script.unpause()
        resumed.append(script)
        if log:
            obj_name = getattr(script.obj, "key", None)
            logger.log_info(f"[Startup] Resuming paused script: {script.key} ({obj_name})")

    return resumed
