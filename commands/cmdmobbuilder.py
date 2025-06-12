"""Command for managing mob prototypes stored by VNUM."""

from typing import Any
import shlex
from evennia.utils.evmenu import EvMenu
from evennia import DefaultRoom
from evennia.utils import evtable
from evennia.utils.search import search_tag

from .command import Command
from utils.mob_proto import (
    get_prototype,
    register_prototype,
    spawn_from_vnum,
)
from world.scripts.mob_db import get_mobdb
from typeclasses.npcs import BaseNPC
from scripts import BuilderAutosave
from commands import npc_builder


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
        try:
            npc = spawn_from_vnum(vnum, location=location)
        except ValueError as err:
            caller.msg(str(err))
            return
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
        npcs = [
            obj
            for obj in search_tag(key=f"M{vnum}", category="vnum")
            if obj.is_typeclass(BaseNPC, exact=False)
        ]
        if npcs:
            caller.msg("Cannot delete - live NPCs exist for that vnum.")
            return
        mob_db.delete_proto(vnum)
        caller.msg(f"Prototype {vnum} deleted.")

    def _sub_edit(self, rest: str):
        caller = self.caller
        autosave = caller.db.builder_autosave
        if rest in ("restore", "discard") and autosave:
            if rest == "restore":
                caller.ndb.buildnpc = dict(autosave)
                caller.ndb.mob_vnum = caller.ndb.buildnpc.get("vnum")
                caller.db.builder_autosave = None
                caller.scripts.add(BuilderAutosave, key="builder_autosave")
                startnode = (
                    "menunode_desc" if caller.ndb.buildnpc.get("key") else "menunode_key"
                )
                EvMenu(
                    caller,
                    "commands.npc_builder",
                    startnode=startnode,
                    cmd_on_exit=npc_builder._on_menu_exit,
                )
            else:
                caller.db.builder_autosave = None
                caller.msg("Autosave discarded.")
            return
        if autosave and rest not in ("restore", "discard"):
            caller.msg("Autosave found. Use '@mobproto/edit restore' to resume or '@mobproto/edit discard' to start over.")
            return
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
        caller.scripts.add(BuilderAutosave, key="builder_autosave")
        startnode = "menunode_desc" if caller.ndb.buildnpc.get("key") else "menunode_key"
        EvMenu(
            caller,
            "commands.npc_builder",
            startnode=startnode,
            cmd_on_exit=npc_builder._on_menu_exit,
        )

    def _sub_diff(self, rest: str):
        caller = self.caller
        parts = rest.split()
        if len(parts) != 2 or not parts[0].isdigit() or not parts[1].isdigit():
            caller.msg("Usage: @mobproto/diff <vnum1> <vnum2>")
            return

        v1, v2 = int(parts[0]), int(parts[1])
        mob_db = get_mobdb()
        p1 = mob_db.get_proto(v1)
        p2 = mob_db.get_proto(v2)
        if not p1 or not p2:
            caller.msg("Prototype not found.")
            return

        table = evtable.EvTable("Field", str(v1), str(v2), border="cells")
        has_diff = False
        fields = sorted(set(p1) | set(p2))
        for field in fields:
            v1_val = p1.get(field, "--")
            v2_val = p2.get(field, "--")
            if isinstance(v1_val, list):
                v1_str = ", ".join(str(v) for v in v1_val)
            else:
                v1_str = str(v1_val)
            if isinstance(v2_val, list):
                v2_str = ", ".join(str(v) for v in v2_val)
            else:
                v2_str = str(v2_val)
            if v1_val != v2_val:
                v1_str = f"|y{v1_str}|n"
                v2_str = f"|y{v2_str}|n"
                has_diff = True
            table.add_row(field, v1_str, v2_str)

        if not has_diff:
            caller.msg("No differences.")
        else:
            caller.msg(str(table))
