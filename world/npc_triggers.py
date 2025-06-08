"""Trigger manager for NPC reactions."""

from __future__ import annotations

from importlib import import_module
from typing import Any

from evennia.utils import make_iter, logger


class TriggerManager:
    """Simple event trigger handler for NPCs.

    Triggers are stored on an object's ``db.triggers`` attribute as a mapping
    from event name to one or more trigger dictionaries.  The new format looks
    like::

        {
            "on_enter": [
                {"match": "", "response": "say Hello"},
                {"match": "player", "response": "attack"},
            ]
        }

    ``match`` is compared case-insensitively against ``message``/``text`` in the
    provided kwargs. ``response`` may be a single command string or a list of
    commands.  Each command is split into ``action`` and ``argument`` and
    executed by the handler.
    """

    def __init__(self, obj: Any, attr: str = "triggers"):
        self.obj = obj
        self.attr = attr

    # internal ---------------------------------------------------------------

    @property
    def _data(self):
        return getattr(self.obj.db, self.attr, {}) or {}

    def _execute(self, action: str, arg: str, **kwargs):
        try:
            if action == "say":
                self.obj.execute_cmd(f"say {arg}")
            elif action in ("emote", "pose"):
                self.obj.execute_cmd(f"{action} {arg}")
            elif action == "move":
                if arg:
                    self.obj.execute_cmd(arg)
            elif action == "attack":
                target = arg or kwargs.get("target")
                if isinstance(target, str):
                    target = self.obj.search(target)
                if target:
                    if not self.obj.in_combat:
                        self.obj.enter_combat(target)
                    else:
                        weapon = self.obj.wielding[0] if self.obj.wielding else self.obj
                        self.obj.attack(target, weapon)
            elif action == "script":
                module, func = arg.rsplit(".", 1)
                mod = import_module(module)
                getattr(mod, func)(self.obj, **kwargs)
            else:
                self.obj.execute_cmd(f"{action} {arg}" if arg else action)
        except Exception as err:  # pragma: no cover - log errors
            logger.log_err(f"NPC trigger error on {self.obj}: {err}")

    # public ----------------------------------------------------------------

    def check(self, event: str, **kwargs):
        """Evaluate triggers for ``event``."""
        triggers = self._data.get(event)
        if not triggers:
            return

        # allow legacy tuple or dict formats
        if isinstance(triggers, tuple):
            triglist = [{"match": triggers[0], "response": triggers[1]}]
        else:
            triglist = make_iter(triggers)

        for trig in triglist:
            if not isinstance(trig, dict):
                continue

            match = trig.get("match")
            if match:
                text = str(kwargs.get("message") or kwargs.get("text") or "")
                if isinstance(match, (list, tuple)):
                    if not any(m.lower() in text.lower() for m in match):
                        continue
                elif str(match).lower() not in text.lower():
                    continue

            responses = (
                trig.get("responses")
                or trig.get("response")
                or trig.get("reactions")
                or trig.get("reaction")
                or []
            )

            for react in make_iter(responses):
                if isinstance(react, str):
                    if " " in react:
                        action, arg = react.split(" ", 1)
                    else:
                        action, arg = react, ""
                elif isinstance(react, dict) and len(react) == 1:
                    action, arg = next(iter(react.items()))
                else:
                    continue
                self._execute(action.lower(), arg, **kwargs)
