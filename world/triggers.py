"""Generic event trigger manager for objects."""

from __future__ import annotations

from importlib import import_module
from typing import Any, Iterable
from random import randint

from datetime import datetime
from evennia.objects.models import ObjectDB
from evennia.utils import make_iter, logger, delay, lazy_property
from utils import eval_safe
from utils.mob_utils import mobprogs_to_triggers
from world.mpcommands import execute_mpcommand


class TriggerMixin:
    """Mixin adding trigger support to a typeclass."""

    #: Attribute name that stores trigger definitions
    triggers_attr: str | None = "triggers"
    #: Optional attribute name holding mob programs to convert on creation
    programs_attr: str | None = None

    @lazy_property
    def trigger_manager(self):
        """Return a :class:`TriggerManager` for this object."""
        return TriggerManager(self, attr=self.triggers_attr)

    def at_object_creation(self):
        super().at_object_creation()
        if self.triggers_attr:
            if getattr(self.db, self.triggers_attr, None) is None:
                setattr(self.db, self.triggers_attr, {})
            if self.programs_attr:
                progs = getattr(self.db, self.programs_attr, None)
                triggers = getattr(self.db, self.triggers_attr, None)
                if progs and not triggers:
                    setattr(self.db, self.triggers_attr, mobprogs_to_triggers(progs))
            self.trigger_manager.start_random_triggers()

    def check_triggers(self, event, **kwargs):
        """Evaluate stored triggers for ``event``."""
        self.trigger_manager.check(event, **kwargs)


class TriggerManager:
    """Simple event trigger handler.

    Triggers are stored on an object's attribute (``attr``) as a mapping
    from event name to one or more trigger dictionaries::

        {
            "on_enter": [
                {"match": "", "response": "say Hello"},
                {"match": "player", "response": "attack"},
            ]
        }

    ``match`` is compared case-insensitively against ``message``/``text`` in the
    provided kwargs. ``response`` may be a single command string or a list of
    commands. Each command is split into ``action`` and ``argument`` and
    executed by the handler.
    """

    ALIASES = {
        "greet_prog": "on_enter",
        "enter_prog": "on_enter",
        "char_enter": "on_enter",
        "leave_prog": "on_leave",
        "char_leave": "on_leave",
        "speech_prog": "on_speak",
        "give_prog": "on_give_item",
        "object_receive": "on_give_item",
        "fight_prog": "on_attack",
        "death_prog": "on_death",
        "death": "on_death",
        "bribe_prog": "on_bribe",
        "random_prog": "random",
        "rand_prog": "random",
        "timer_prog": "on_timer",
        "get_prog": "on_get",
        "drop_prog": "on_drop",
        "wear_prog": "on_wear",
        "remove_prog": "on_remove",
        "sac_prog": "on_sacrifice",
        "time_prog": "time",
        "hour_prog": "hour",
    }

    def __init__(self, obj: Any, attr: str | None = None):
        """Create manager for ``obj``.

        If ``attr`` is omitted the handler checks for ``obj.db.obj_triggers``
        and ``obj.db.room_triggers`` before falling back to ``triggers``.
        """

        self.obj = obj
        if attr:
            self.attr = attr
        elif getattr(obj.db, "obj_triggers", None) is not None:
            self.attr = "obj_triggers"
        elif getattr(obj.db, "room_triggers", None) is not None:
            self.attr = "room_triggers"
        else:
            self.attr = "triggers"

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
                    if not getattr(self.obj, "in_combat", False):
                        if hasattr(self.obj, "enter_combat"):
                            self.obj.enter_combat(target)
                    else:
                        weapon = self.obj.wielding[0] if getattr(self.obj, "wielding", []) else self.obj
                        if hasattr(self.obj, "attack"):
                            self.obj.attack(target, weapon)
            elif action == "script":
                module, func = arg.rsplit(".", 1)
                mod = import_module(module)
                getattr(mod, func)(self.obj, **kwargs)
            elif action == "mob":
                execute_mpcommand(self.obj, arg)
            else:
                self.obj.execute_cmd(f"{action} {arg}" if arg else action)
        except Exception as err:  # pragma: no cover - log errors
            logger.log_err(f"Trigger error on {self.obj}: {err}")

    # public ----------------------------------------------------------------

    def _alias_events(self, event: str) -> list[str]:
        """Return list of event and any aliases."""
        events = [event]
        if alias := self.ALIASES.get(event):
            events.append(alias)
        for key, val in self.ALIASES.items():
            if val == event:
                events.append(key)
        return list(dict.fromkeys(events))

    def _evaluate(self, trig: dict, **kwargs):
        # evaluate optional conditions expression
        cond_expr = trig.get("conditions")
        if isinstance(cond_expr, str):
            sandbox = {
                "caller": kwargs.get("caller")
                or kwargs.get("chara")
                or kwargs.get("looker")
                or kwargs.get("speaker"),
                "npc": self.obj,
                "item": kwargs.get("item"),
                "room": getattr(self.obj, "location", None),
            }
            sandbox.update(kwargs)
            if not eval_safe(cond_expr, sandbox):
                return

        match = trig.get("match")
        if match:
            text = str(kwargs.get("message") or kwargs.get("text") or "")
            if isinstance(match, (list, tuple)):
                if not any(m.lower() in text.lower() for m in match):
                    return
            elif str(match).lower() not in text.lower():
                return

        percent = trig.get("percent")
        if percent is not None and randint(1, 100) > int(percent):
            return

        combat = trig.get("combat")
        if combat is not None and bool(getattr(self.obj, "in_combat", False)) != bool(combat):
            return

        bribe = trig.get("bribe")
        if bribe is not None and kwargs.get("amount", kwargs.get("bribe_amount", 0)) < bribe:
            return

        hp_pct = trig.get("hp_pct")
        if hp_pct is not None:
            try:
                cur = self.obj.traits.health.value
                maxhp = self.obj.traits.health.max or 1
                if (cur / maxhp) * 100 > float(hp_pct):
                    return
            except Exception:
                return

        hour = trig.get("hour")
        if hour is not None and kwargs.get("hour") != hour:
            return

        time_val = trig.get("time")
        if time_val is not None and kwargs.get("time") != time_val:
            return

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

    def _collect_triggers(self, events: Iterable[str]):
        for ev in events:
            trigdata = self._data.get(ev)
            if not trigdata:
                continue
            if isinstance(trigdata, tuple):
                yield {"match": trigdata[0], "response": trigdata[1]}
            else:
                for trig in make_iter(trigdata):
                    if isinstance(trig, dict):
                        yield trig

    def check(self, event: str, **kwargs):
        """Evaluate triggers for ``event`` (including aliases)."""
        events = self._alias_events(event)
        trigs = list(self._collect_triggers(events))
        if not trigs:
            return
        for trig in trigs:
            self._evaluate(trig, **kwargs)

    # random trigger helpers -------------------------------------------------
    def _run_random_trigger(self, trig: dict):
        self._evaluate(trig)
        interval = int(trig.get("interval", 60))
        delay(interval, self._run_random_trigger, trig, persistent=True)

    def start_random_triggers(self):
        """Schedule callbacks for any random triggers."""
        events = self._alias_events("random")
        for trig in self._collect_triggers(events):
            interval = int(trig.get("interval", 60))
            delay(interval, self._run_random_trigger, trig, persistent=True)


def _iter_time_trigger_objects():
    """Yield pairs of objects and attribute names that may hold time triggers."""
    attrs = ("triggers", "obj_triggers", "room_triggers")
    seen = set()
    for attr in attrs:
        for obj in ObjectDB.objects.get_by_attribute(key=attr):
            if obj.id in seen:
                continue
            seen.add(obj.id)
            yield obj, attr


def process_hour_triggers(current_time: datetime | None = None):
    """Check all objects for hour-based triggers."""
    now = current_time or datetime.now()
    hour = now.hour
    for obj, attr in _iter_time_trigger_objects():
        TriggerManager(obj, attr=attr).check("hour", hour=hour)


def process_time_triggers(current_time: datetime | None = None):
    """Check all objects for time-based triggers."""
    now = current_time or datetime.now()
    timestr = now.strftime("%H:%M")
    for obj, attr in _iter_time_trigger_objects():
        TriggerManager(obj, attr=attr).check("time", time=timestr)
