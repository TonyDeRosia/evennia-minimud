import shlex
import json

from typeclasses.npcs import BaseNPC
from evennia.utils import evtable
from evennia.objects.models import ObjectDB

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
    """
    Inspect an NPC or stored prototype.

    Prototype data is read from ``world/prototypes/npcs.json``. This is a
    read-only command and will not change any existing NPCs. Use ``@medit`` if
    you need to update a live NPC from a prototype.

    Usage:
        @mstat <npc or proto>

    Example:
        @mstat bandit
    """

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
        table = evtable.EvTable("|cAttribute|n", "|cValue|n", border="cells")

        highlight = {"key", "level", "npc_class"}
        special = {
            "actflags",
            "affected_by",
            "saving_throws",
            "attack_types",
            "defense_types",
            "ris",
            "languages",
        }

        for field, value in data.items():
            if field == "edit_obj" or field in special:
                continue
            if isinstance(value, list):
                valstr = ", ".join(str(v) for v in value)
            else:
                valstr = str(value)
            if field in highlight:
                valstr = f"|w{valstr}|n"
            table.add_row(f"|c{field.replace('_', ' ').title()}|n", valstr)

        flags = []
        flags.extend(data.get("actflags", []))
        flags.extend(data.get("affected_by", []))
        table.add_row("|cFlags|n", ", ".join(flags) if flags else "--")
        table.add_row(
            "|cSaves|n",
            ", ".join(data.get("saving_throws", []))
            if data.get("saving_throws")
            else "--",
        )
        table.add_row(
            "|cAttacks|n",
            ", ".join(data.get("attack_types", []))
            if data.get("attack_types")
            else "--",
        )
        table.add_row(
            "|cDefenses|n",
            ", ".join(data.get("defense_types", []))
            if data.get("defense_types")
            else "--",
        )
        table.add_row(
            "|cResists|n",
            ", ".join(data.get("ris", [])) if data.get("ris") else "--",
        )
        table.add_row(
            "|cLanguages|n",
            ", ".join(data.get("languages", [])) if data.get("languages") else "--",
        )

        header = f"|Y[ NPC STATS: {data.get('key', 'Unknown')} ]|n"
        self.msg(header)
        self.msg(str(table))


class CmdMCreate(Command):
    """
    Create a new NPC prototype.

    The prototype is stored in ``world/prototypes/npcs.json`` and does not
    affect any already spawned NPCs. Use ``@medit`` later if you need to update
    a live NPC from the saved prototype.

    Usage:
        @mcreate <key> [copy_key]

    Example:
        @mcreate guard_02 basic_guard
    """

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
    """
    Edit a field on an NPC prototype.

    Changes are written to ``world/prototypes/npcs.json``. Existing NPCs are
    unaffected until you apply the prototype with ``@medit``.

    Usage:
        @mset <key> <field> <value>

    Example:
        @mset bandit level 5
    """

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
        "resistances": lambda s: [f.value for f in parse_flag_list(s, RIS_TYPES)],
        "attack_types": lambda s: [f.value for f in parse_flag_list(s, ATTACK_TYPES)],
        "defense_types": lambda s: [f.value for f in parse_flag_list(s, DEFENSE_TYPES)],
        "skills": lambda s: [p.strip() for p in s.split(',') if p.strip()],
        "spells": lambda s: [p.strip() for p in s.split(',') if p.strip()],
        "special_funcs": lambda s: [f.value for f in parse_flag_list(s, SPECIAL_FUNCS)],
        "loot_table": json.loads,
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
    """
    List stored NPC prototypes or spawned NPCs.

    Prototype information is read from ``world/prototypes/npcs.json``. Listing
    does not alter any existing NPCs. Use ``@medit`` if you want to modify a
    spawned NPC.

    Usage:
        @mlist [area] [/room|/area] [filters]

    Example:
        @mlist /room
    """

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
        args = self.args.strip().split()

        area = None
        rangestr = None
        filter_by: dict = {}
        show_room = False
        show_area = False

        for part in args:
            low = part.lower()
            if low.startswith("/"):
                if low == "/room":
                    show_room = True
                elif low == "/area":
                    show_area = True
                continue
            if "=" in part:
                k, v = part.split("=", 1)
                k = k.lower()
                if k in {"class", "race", "role", "tag", "zone"}:
                    filter_by[k] = v
                continue
            if "-" in part and not rangestr:
                rangestr = part
                continue
            if not area:
                area = part

        all_reg = prototypes.get_npc_prototypes()
        registry_list = prototypes.filter_npc_prototypes(all_reg, filter_by)
        registry = dict(registry_list)

        if show_room or show_area:
            if show_room:
                npcs = [
                    obj
                    for obj in self.caller.location.contents
                    if obj.is_typeclass(BaseNPC, exact=False)
                ]
            else:
                area_name = self.caller.location.db.area
                if not area_name:
                    self.msg("This room has no area set.")
                    return
                npcs = [
                    obj
                    for obj in ObjectDB.objects.get_by_attribute(
                        key="area_tag", value=area_name
                    )
                    if obj.is_typeclass(BaseNPC, exact=False)
                ]

            counts = {}
            for npc in npcs:
                key = npc.db.prototype_key
                if not key or key not in registry:
                    continue
                counts[key] = counts.get(key, 0) + 1
            keys = sorted(counts)
        else:
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
            counts = {
                key: ObjectDB.objects.get_by_attribute(
                    key="prototype_key", value=key
                ).count()
                for key in keys
            }

        if not keys:
            self.msg("No prototypes found.")
            return

        table = evtable.EvTable("Key", "Lvl", "Class", "Roles", "Count", border="cells")
        for key in keys:
            proto = registry.get(key)
            if not proto:
                continue
            roles = proto.get("roles") or []
            if isinstance(roles, str):
                roles = [roles]
            table.add_row(
                key,
                str(proto.get("level", "-")),
                proto.get("npc_class", "-"),
                ", ".join(roles) if roles else "-",
                str(counts.get(key, 0)),
            )

        self.msg(str(table))


class CmdMakeShop(Command):
    """Add basic shop data to an NPC prototype."""

    key = "@makeshop"
    locks = "cmd:perm(Builder) or perm(Admin) or perm(Developer)"
    help_category = "Building"

    def func(self):
        proto_key = self.args.strip()
        if not proto_key:
            self.msg("Usage: @makeshop <prototype>")
            return
        registry = prototypes.get_npc_prototypes()
        proto = registry.get(proto_key)
        if not proto:
            self.msg("Prototype not found.")
            return
        proto = dict(proto)
        if proto.get("shop"):
            self.msg("Shop data already exists on that prototype.")
            return
        proto["shop"] = {
            "buy_percent": 100,
            "sell_percent": 100,
            "hours": "0-24",
            "item_types": [],
        }
        prototypes.register_npc_prototype(proto_key, proto)
        self.msg(f"Shop created for {proto_key}.")


class CmdShopSet(Command):
    """Edit shop fields on an NPC prototype."""

    key = "@shopset"
    locks = "cmd:perm(Builder) or perm(Admin) or perm(Developer)"
    help_category = "Building"

    def parse(self):
        try:
            parts = shlex.split(self.args)
        except ValueError:
            parts = []
        if len(parts) >= 3:
            self.proto_key = parts[0]
            self.field = parts[1].lower()
            self.value = " ".join(parts[2:])
        else:
            self.proto_key = self.field = self.value = None

    def func(self):
        if not self.proto_key:
            self.msg("Usage: @shopset <proto> <buy|sell|hours|types> <value>")
            return
        registry = prototypes.get_npc_prototypes()
        proto = registry.get(self.proto_key)
        if not proto or "shop" not in proto:
            self.msg("Prototype not found or has no shop data.")
            return
        shop = dict(proto.get("shop", {}))
        if self.field == "buy":
            try:
                shop["buy_percent"] = int(self.value)
            except (TypeError, ValueError):
                self.msg("Buy percent must be an integer.")
                return
        elif self.field == "sell":
            try:
                shop["sell_percent"] = int(self.value)
            except (TypeError, ValueError):
                self.msg("Sell percent must be an integer.")
                return
        elif self.field == "hours":
            shop["hours"] = self.value
        elif self.field == "types":
            shop["item_types"] = [t.strip() for t in self.value.split(",") if t.strip()]
        else:
            self.msg("Unknown field. Use buy, sell, hours or types.")
            return
        proto = dict(proto)
        proto["shop"] = shop
        prototypes.register_npc_prototype(self.proto_key, proto)
        self.msg(f"{self.field} updated on {self.proto_key}.")


class CmdShopStat(Command):
    """Display shop data for an NPC prototype."""

    key = "@shopstat"
    locks = "cmd:perm(Builder) or perm(Admin) or perm(Developer)"
    help_category = "Building"

    def func(self):
        proto_key = self.args.strip()
        if not proto_key:
            self.msg("Usage: @shopstat <prototype>")
            return
        proto = prototypes.get_npc_prototypes().get(proto_key)
        if not proto or "shop" not in proto:
            self.msg("No shop data for that prototype.")
            return
        shop = proto["shop"]
        lines = [
            f"Buy Percent: {shop.get('buy_percent', 0)}",
            f"Sell Percent: {shop.get('sell_percent', 0)}",
            f"Hours: {shop.get('hours', '')}",
            f"Item Types: {', '.join(shop.get('item_types', []))}",
        ]
        self.msg("\n".join(lines))


class CmdMakeRepair(Command):
    """Add repair shop data to an NPC prototype."""

    key = "@makerepair"
    locks = "cmd:perm(Builder) or perm(Admin) or perm(Developer)"
    help_category = "Building"

    def func(self):
        proto_key = self.args.strip()
        if not proto_key:
            self.msg("Usage: @makerepair <prototype>")
            return
        registry = prototypes.get_npc_prototypes()
        proto = registry.get(proto_key)
        if not proto:
            self.msg("Prototype not found.")
            return
        proto = dict(proto)
        if proto.get("repair"):
            self.msg("Repair data already exists on that prototype.")
            return
        proto["repair"] = {
            "cost_percent": 100,
            "hours": "0-24",
            "item_types": [],
        }
        prototypes.register_npc_prototype(proto_key, proto)
        self.msg(f"Repair shop created for {proto_key}.")


class CmdRepairSet(Command):
    """Edit repair shop data on an NPC prototype."""

    key = "@repairset"
    locks = "cmd:perm(Builder) or perm(Admin) or perm(Developer)"
    help_category = "Building"

    def parse(self):
        try:
            parts = shlex.split(self.args)
        except ValueError:
            parts = []
        if len(parts) >= 3:
            self.proto_key = parts[0]
            self.field = parts[1].lower()
            self.value = " ".join(parts[2:])
        else:
            self.proto_key = self.field = self.value = None

    def func(self):
        if not self.proto_key:
            self.msg("Usage: @repairset <proto> <cost|hours|types> <value>")
            return
        registry = prototypes.get_npc_prototypes()
        proto = registry.get(self.proto_key)
        if not proto or "repair" not in proto:
            self.msg("Prototype not found or has no repair data.")
            return
        repair = dict(proto.get("repair", {}))
        if self.field == "cost":
            try:
                repair["cost_percent"] = int(self.value)
            except (TypeError, ValueError):
                self.msg("Cost percent must be an integer.")
                return
        elif self.field == "hours":
            repair["hours"] = self.value
        elif self.field == "types":
            repair["item_types"] = [
                t.strip() for t in self.value.split(",") if t.strip()
            ]
        else:
            self.msg("Unknown field. Use cost, hours or types.")
            return
        proto = dict(proto)
        proto["repair"] = repair
        prototypes.register_npc_prototype(self.proto_key, proto)
        self.msg(f"{self.field} updated on {self.proto_key}.")


class CmdRepairStat(Command):
    """Display repair shop data for an NPC prototype."""

    key = "@repairstat"
    locks = "cmd:perm(Builder) or perm(Admin) or perm(Developer)"
    help_category = "Building"

    def func(self):
        proto_key = self.args.strip()
        if not proto_key:
            self.msg("Usage: @repairstat <prototype>")
            return
        proto = prototypes.get_npc_prototypes().get(proto_key)
        if not proto or "repair" not in proto:
            self.msg("No repair data for that prototype.")
            return
        repair = proto["repair"]
        lines = [
            f"Cost Percent: {repair.get('cost_percent', 0)}",
            f"Hours: {repair.get('hours', '')}",
            f"Item Types: {', '.join(repair.get('item_types', []))}",
        ]
        self.msg("\n".join(lines))


class CmdMobValidate(Command):
    """Validate a stored NPC prototype for common issues."""

    key = "@mobvalidate"
    locks = "cmd:perm(Builder) or perm(Admin) or perm(Developer)"
    help_category = "Building"

    def func(self):
        proto_key = self.args.strip()
        if not proto_key:
            self.msg("Usage: @mobvalidate <prototype>")
            return
        proto = prototypes.get_npc_prototypes().get(proto_key)
        if not proto:
            self.msg("Prototype not found.")
            return
        warnings = npc_builder.validate_prototype(proto)
        if warnings:
            lines = ["Warnings:"] + [f" - {w}" for w in warnings]
            self.msg("\n".join(lines))
        else:
            self.msg("No issues found.")
