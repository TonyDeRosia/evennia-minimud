# Help file editor

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict

from django.conf import settings
from evennia.utils.evmenu import EvMenu
from evennia.utils.eveditor import EvEditor

from .command import Command


_HELP_PATH = Path(settings.GAME_DIR) / "world" / "prototypes" / "helpfiles.json"


# ------------------------------------------------------------
# File helpers
# ------------------------------------------------------------

def _load_helpfiles() -> Dict[str, Dict]:
    try:
        with _HELP_PATH.open("r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError:
        return {}


def _save_helpfiles(data: Dict[str, Dict]):
    _HELP_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _HELP_PATH.open("w") as f:
        json.dump(data, f, indent=4)


# ------------------------------------------------------------
# Menu helpers
# ------------------------------------------------------------

def _summary(caller) -> str:
    proto = caller.ndb.help_proto or {}
    key = caller.ndb.help_key
    lines = [f"|wEditing help '{key}'|n"]
    level = proto.get("level")
    if level is not None:
        lines.append(f"Level: {level}")
    text = proto.get("text", "")
    if text:
        preview = text.splitlines()[0]
        if len(preview) > 40:
            preview = preview[:37] + "..."
        lines.append(f"Text: {preview}")
    return "\n".join(lines)


# ------------------------------------------------------------
# Menu nodes
# ------------------------------------------------------------

def menunode_main(caller, raw_string="", **kwargs):
    text = _summary(caller)
    options = [
        {"desc": "Edit level", "goto": "menunode_level"},
        {"desc": "Edit text", "goto": "menunode_text"},
        {"desc": "Save & quit", "goto": "menunode_done"},
        {"desc": "Cancel", "goto": "menunode_cancel"},
    ]
    return text, options


# level editing

def menunode_level(caller, raw_string="", **kwargs):
    current = caller.ndb.help_proto.get("level", 0)
    text = f"|wLevel|n [current: {current}]"
    options = {"key": "_default", "goto": _set_level}
    return text, options


def _set_level(caller, raw_string, **kwargs):
    if not raw_string.strip().isdigit():
        caller.msg("Level must be a number.")
        return "menunode_level"
    caller.ndb.help_proto["level"] = int(raw_string.strip())
    return "menunode_main"


# text editing

def menunode_text(caller, raw_string="", **kwargs):
    def loadfunc(caller):
        return caller.ndb.help_proto.get("text", "")

    def savefunc(caller, buf):
        caller.ndb.help_proto["text"] = buf

    def quitfunc(caller, buf):
        caller.ndb.help_proto["text"] = buf
        EvMenu(caller, "commands.hedit", startnode="menunode_main")

    EvEditor(caller, loadfunc=loadfunc, savefunc=savefunc, quitfunc=quitfunc, key="HEditor")
    return None


# finalization

def menunode_done(caller, raw_string="", **kwargs):
    data = _load_helpfiles()
    key = caller.ndb.help_key
    data[key] = caller.ndb.help_proto
    _save_helpfiles(data)
    caller.msg(f"Help entry '{key}' saved.")
    caller.ndb.help_key = None
    caller.ndb.help_proto = None
    return None


def menunode_cancel(caller, raw_string="", **kwargs):
    caller.msg("Editing cancelled.")
    caller.ndb.help_key = None
    caller.ndb.help_proto = None
    return None


# ------------------------------------------------------------
# Command class
# ------------------------------------------------------------

class CmdHEdit(Command):
    """Edit or create a help entry."""

    key = "hedit"
    locks = "cmd:perm(Builder)"
    help_category = "Building"

    def func(self):
        if not self.args:
            self.msg("Usage: hedit <keyword>")
            return
        key = self.args.strip().lower()
        data = _load_helpfiles()
        proto = data.get(key, {"level": 0, "text": ""})
        self.caller.ndb.help_key = key
        self.caller.ndb.help_proto = dict(proto)
        EvMenu(self.caller, "commands.hedit", startnode="menunode_main")

