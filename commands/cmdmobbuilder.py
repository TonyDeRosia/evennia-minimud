"""Command for managing mob prototypes stored by VNUM."""

from typing import Any
import shlex
from evennia.utils.evmenu import EvMenu
from evennia import DefaultRoom

from .command import Command
from utils.mob_proto import (
    get_prototype,
    register_prototype,
    spawn_from_vnum,
)
from world.scripts.mob_db import get_mobdb


class CmdMobProto(Command):
    """Manage mob prototypes by VNUM."""

    key = "@mobproto"
    locks = "cmd:perm(Builder)"
    help_category = "Building"

    def func(self):
        caller = self.caller
        if not self.args:
            caller.msg("Usage: @mobproto <create|set|list|spawn|delete|edit|diff>")
            return

        parts = self.args.split(None, 1)
        sub = parts[0].lower()
        rest = parts[1].strip() if len(parts) > 1 else ""

        if sub == "create":
            self._sub_create(rest)
        elif sub == "set":
            self._sub_set(rest)
        elif sub == "list":
            self._sub_list()
        elif sub == "spawn":
            self._sub_spawn(rest)
        elif sub == "delete":
            self._sub_delete(rest)
        elif sub == "edit":
            self._sub_edit(rest)
        elif sub == "diff":
            self._sub_diff(rest)
        else:
            caller.msg("Unknown subcommand.")

    # ---------------------------------------------------------------
    # subcommands
    # ---------------------------------------------------------------
    def _sub_create(self, rest: str):
        caller = self.caller
        parts = rest.split(None, 1)
        if len(parts) != 2 or not parts[0].isdigit():
            caller.msg("Usage: @mobproto/create <vnum> <name>")
            return
        vnum = int(parts[0])
        name = parts[1]
        if get_prototype(vnum):
            caller.msg("Prototype already exists.")
            return
        register_prototype({"key": name}, vnum=vnum)
        caller.msg(f"Prototype {vnum} created.")

    def _sub_set(self, rest: str):
        caller = self.caller
        try:
            parts = shlex.split(rest)
        except ValueError:
            parts = []
        if len(parts) < 3 or not parts[0].isdigit():
            caller.msg("Usage: @mobproto/set <vnum> <field> <value>")
            return
        vnum = int(parts[0])
        field = parts[1]
        value = " ".join(parts[2:])
        proto = get_prototype(vnum)
        if not proto:
            caller.msg("Prototype not found.")
            return
        if value.isdigit():
            val: Any = int(value)
        else:
            try:
                val = float(value)
            except ValueError:
                val = value
        proto = dict(proto)
        proto[field] = val
        register_prototype(proto, vnum=vnum)
        caller.msg(f"Field {field} updated on {vnum}.")

    def _sub_list(self):
        caller = self.caller
        mob_db = get_mobdb()
        if not mob_db.db.vnums:
            caller.msg("No mob prototypes registered.")
            return
        lines = ["|wVNUM|n |wName|n |wSpawns|n"]
        for vnum, proto in sorted(mob_db.db.vnums.items()):
            name = proto.get("key", "--")
            count = proto.get("spawn_count", 0)
            lines.append(f"{vnum:>5} {name} {count}")
        caller.msg("\n".join(lines))

    def _sub_spawn(self, rest: str):
        caller = self.caller
        parts = rest.split(None, 1)
        if not parts or not parts[0].isdigit():
            caller.msg("Usage: @mobproto/spawn <vnum> [room]")
            return
        vnum = int(parts[0])
        location = caller.location
        if len(parts) > 1:
            room = caller.search(parts[1], global_search=True)
            if room and room.is_typeclass(DefaultRoom, exact=False):
                location = room
            else:
                caller.msg("Invalid room.")
                return
        npc = spawn_from_vnum(vnum, location=location)
        if not npc:
            caller.msg("Prototype not found.")
        else:
            caller.msg(f"Spawned {npc.key} (vnum {vnum}).")

    def _sub_delete(self, rest: str):
        caller = self.caller
        if not rest.isdigit():
            caller.msg("Usage: @mobproto/delete <vnum>")
            return
        vnum = int(rest)
        mob_db = get_mobdb()
        if not mob_db.get_proto(vnum):
            caller.msg("Prototype not found.")
            return
        mob_db.delete_proto(vnum)
        caller.msg(f"Prototype {vnum} deleted.")

    def _sub_edit(self, rest: str):
        caller = self.caller
        if not rest.isdigit():
            caller.msg("Usage: @mobproto/edit <vnum>")
            return
        vnum = int(rest)
        proto = get_prototype(vnum)
        if not proto:
            caller.msg("Prototype not found.")
            return
        caller.ndb.buildnpc = dict(proto)
        caller.ndb.mob_vnum = vnum
        EvMenu(caller, "commands.npc_builder", startnode="menunode_desc")

    def _sub_diff(self, rest: str):
        caller = self.caller
        parts = rest.split()
        if len(parts) != 2 or not parts[0].isdigit() or not parts[1].isdigit():
            caller.msg("Usage: @mobproto/diff <vnum1> <vnum2>")
            return
        v1, v2 = int(parts[0]), int(parts[1])
        p1 = get_prototype(v1)
        p2 = get_prototype(v2)
        if not p1 or not p2:
            caller.msg("Prototype not found.")
            return
        fields = set(p1) | set(p2)
        diff_lines = [f"|wField|n : {v1} -> {v2}"]
        for field in sorted(fields):
            if p1.get(field) != p2.get(field):
                diff_lines.append(f"{field}: {p1.get(field, '--')} -> {p2.get(field, '--')}")
        if len(diff_lines) == 1:
            caller.msg("No differences.")
        else:
            caller.msg("\n".join(diff_lines))

