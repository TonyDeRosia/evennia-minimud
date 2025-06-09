import shlex

from typeclasses.npcs import BaseNPC
from evennia.utils import evtable

from .command import Command
from . import npc_builder
from world import prototypes, area_npcs
from world.mob_constants import (
    NPC_RACES,
    NPC_CLASSES,
    ACTFLAGS,
    AFFECTED_BY,
    LANGUAGES,
    BODYPARTS,
    SAVING_THROWS,
    RIS_TYPES,
    ATTACK_TYPES,
    DEFENSE_TYPES,
    SPECIAL_FUNCS,
    parse_flag_list,
)

class CmdMStat(Command):
    """Inspect an NPC or prototype."""

    key = "@mstat"
    locks = "cmd:perm(Builder) or perm(Admin) or perm(Developer)"
    help_category = "Building"

    def func(self):
        if not self.args:
            self.msg("Usage: @mstat <npc or proto>")
            return
        arg = self.args.strip()
        registry = prototypes.get_npc_prototypes()
        proto = registry.get(arg)
        if proto:
            data = proto
        else:
            target = self.caller.search(arg, global_search=True)
            if not target or not target.is_typeclass(BaseNPC, exact=False):
                self.msg("NPC or prototype not found.")
                return
            data = npc_builder._gather_npc_data(target)
        table = evtable.EvTable("Attribute", "Value")
        for field, value in data.items():
            if field == "edit_obj":
                continue
            if isinstance(value, list):
                valstr = ", ".join(str(v) for v in value)
            else:
                valstr = str(value)
            table.add_row(field, valstr)
        self.msg(str(table))


class CmdMCreate(Command):
    """Create a new NPC prototype."""

    key = "@mcreate"
    locks = "cmd:perm(Builder) or perm(Admin) or perm(Developer)"
    help_category = "Building"

    def parse(self):
        parts = self.args.split(None, 1)
        self.new_key = parts[0].strip() if parts else ""
        self.copy_key = parts[1].strip() if len(parts) > 1 else ""

    def func(self):
        if not self.new_key:
            self.msg("Usage: @mcreate <key> [copy_key]")
            return
        registry = prototypes.get_npc_prototypes()
        if self.new_key in registry:
            self.msg("Prototype with that key already exists.")
            return
        proto = {}
        if self.copy_key:
            proto = registry.get(self.copy_key)
            if not proto:
                self.msg("Copy prototype not found.")
                return
            proto = dict(proto)
        proto["key"] = self.new_key
        prototypes.register_npc_prototype(self.new_key, proto)
        self.msg(f"Prototype {self.new_key} created.")


class CmdMSet(Command):
    """Edit a field on an NPC prototype."""

    key = "@mset"
    locks = "cmd:perm(Builder) or perm(Admin) or perm(Developer)"
    help_category = "Building"

    _FIELD_CASTS = {
        "level": int,
        "race": lambda s: NPC_RACES.from_str(s).value,
        "npc_class": lambda s: NPC_CLASSES.from_str(s).value,
        "actflags": lambda s: [f.value for f in parse_flag_list(s, ACTFLAGS)],
        "affected_by": lambda s: [f.value for f in parse_flag_list(s, AFFECTED_BY)],
        "languages": lambda s: [f.value for f in parse_flag_list(s, LANGUAGES)],
        "bodyparts": lambda s: [f.value for f in parse_flag_list(s, BODYPARTS)],
        "saving_throws": lambda s: [f.value for f in parse_flag_list(s, SAVING_THROWS)],
        "ris": lambda s: [f.value for f in parse_flag_list(s, RIS_TYPES)],
        "attack_types": lambda s: [f.value for f in parse_flag_list(s, ATTACK_TYPES)],
        "defense_types": lambda s: [f.value for f in parse_flag_list(s, DEFENSE_TYPES)],
        "special_funcs": lambda s: [f.value for f in parse_flag_list(s, SPECIAL_FUNCS)],
    }

    def parse(self):
        try:
            parts = shlex.split(self.args)
        except ValueError:
            parts = []
        if len(parts) >= 3:
            self.proto_key = parts[0]
            self.field = parts[1]
            self.value = " ".join(parts[2:])
        else:
            self.proto_key = self.field = self.value = None

    def func(self):
        if not self.proto_key:
            self.msg("Usage: @mset <key> <field> <value>")
            return
        registry = prototypes.get_npc_prototypes()
        proto = registry.get(self.proto_key)
        if not proto:
            self.msg("Prototype not found.")
            return
        cast = self._FIELD_CASTS.get(self.field, str)
        if cast is int:
            try:
                val = int(self.value)
            except (TypeError, ValueError):
                self.msg("Value must be an integer.")
                return
        elif callable(cast):
            try:
                val = cast(self.value)
            except ValueError:
                self.msg("Invalid value for field.")
                return
        else:
            val = self.value
        proto = dict(proto)
        proto[self.field] = val
        prototypes.register_npc_prototype(self.proto_key, proto)
        self.msg(f"{self.field} updated on {self.proto_key}.")

class CmdMList(Command):
    """List NPC prototypes optionally filtered by area and range."""

    key = "@mlist"
    locks = "cmd:perm(Builder) or perm(Admin) or perm(Developer)"
    help_category = "Building"

    def _parse_range(self, spec):
        if "-" not in spec:
            return None
        start, end = spec.split("-", 1)
        if start.isdigit() and end.isdigit():
            return ("num", int(start), int(end))
        if len(start) == 1 and len(end) == 1 and start.isalpha() and end.isalpha():
            return ("alpha", start.lower(), end.lower())
        return None

    def func(self):
        area = None
        rangestr = None
        parts = self.args.strip().split()
        if parts:
            if len(parts) == 2:
                area, rangestr = parts
            else:
                part = parts[0]
                if "-" in part:
                    rangestr = part
                else:
                    area = part
        registry = prototypes.get_npc_prototypes()
        if area:
            keys = area_npcs.get_area_npc_list(area)
            if not keys:
                self.msg("No prototypes registered for that area.")
                return
        else:
            keys = list(registry.keys())
        keys = sorted(keys)
        if rangestr:
            rdata = self._parse_range(rangestr)
            if not rdata:
                self.msg("Invalid range specification.")
                return
            rtype, a, b = rdata
            if rtype == "num":
                a = max(1, a)
                b = min(len(keys), b)
                keys = keys[a - 1 : b]
            else:
                keys = [k for k in keys if a <= k[0].lower() <= b]
        lines = []
        for key in keys:
            desc = registry.get(key, {}).get("desc", "")
            lines.append(f"{key} - {desc}" if desc else key)
        if not lines:
            self.msg("No prototypes found.")
        else:
            self.msg("\n".join(lines))
