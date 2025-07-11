import shlex
import json
from pathlib import Path
from django.conf import settings

from typeclasses.npcs import BaseNPC
from evennia.utils import evtable
from evennia.server.models import ServerConfig
from evennia.objects.models import ObjectDB
from world.scripts.mob_db import get_mobdb
from utils.prototype_manager import load_all_prototypes

from .command import Command
from . import npc_builder
from world import prototypes, area_npcs
from world.areas import get_areas, find_area_by_vnum, get_area_vnum_range
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
    read-only command and will not change any existing NPCs. Use ``@editnpc`` if
    you need to update a live NPC from a prototype. Use ``/rom`` for a ROM-style
    summary instead of the default table.

    Usage:
        @mstat [/rom] <npc or proto>

    Example:
        @mstat bandit
        @mstat /rom bandit
    """

    key = "@mstat"
    locks = "cmd:perm(Builder) or perm(Admin) or perm(Developer)"
    help_category = "Building"

    def parse(self):
        parts = self.args.strip().split()
        self.use_rom = False
        clean = []
        for part in parts:
            if part.lower() == "/rom":
                self.use_rom = True
            else:
                clean.append(part)
        self.target = " ".join(clean)

    def _format_rom(self, data: dict) -> str:
        """Return ROM-style stats for ``data``."""

        lines = [f"Name: {data.get('key', 'Unknown')}"]
        lines.append(
            f"Level: {data.get('level', '--')}  Race: {data.get('race', '--')}  "
            f"Class: {data.get('npc_type', '--')}"
        )
        lines.append(
            f"Hit Points: {data.get('hp', '--')}  Damage: {data.get('damage', '--')}  "
            f"Armor: {data.get('armor', '--')}"
        )
        flags = []
        flags.extend(data.get("actflags", []))
        flags.extend(data.get("affected_by", []))
        lines.append("Flags: " + (", ".join(flags) if flags else "--"))
        lines.append(
            "Saves: "
            + (
                ", ".join(data.get("saving_throws", []))
                if data.get("saving_throws")
                else "--"
            )
        )
        lines.append(
            "Attacks: "
            + (
                ", ".join(data.get("attack_types", []))
                if data.get("attack_types")
                else "--"
            )
        )
        lines.append(
            "Defenses: "
            + (
                ", ".join(data.get("defense_types", []))
                if data.get("defense_types")
                else "--"
            )
        )
        lines.append(
            "Resists: "
            + (
                ", ".join(data.get("resistances", []))
                if data.get("resistances")
                else "--"
            )
        )
        lines.append(
            "Languages: "
            + (", ".join(data.get("languages", [])) if data.get("languages") else "--")
        )
        return "\n".join(lines)

    def func(self):
        if not getattr(self, "target", None):
            self.msg("Usage: @mstat <npc or proto>")
            return
        arg = self.target
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

        highlight = {"key", "level", "npc_type"}
        special = {
            "actflags",
            "affected_by",
            "saving_throws",
            "attack_types",
            "defense_types",
            "resistances",
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
            (
                ", ".join(data.get("saving_throws", []))
                if data.get("saving_throws")
                else "--"
            ),
        )
        table.add_row(
            "|cAttacks|n",
            (
                ", ".join(data.get("attack_types", []))
                if data.get("attack_types")
                else "--"
            ),
        )
        table.add_row(
            "|cDefenses|n",
            (
                ", ".join(data.get("defense_types", []))
                if data.get("defense_types")
                else "--"
            ),
        )
        table.add_row(
            "|cResists|n",
            ", ".join(data.get("resistances", [])) if data.get("resistances") else "--",
        )
        table.add_row(
            "|cLanguages|n",
            ", ".join(data.get("languages", [])) if data.get("languages") else "--",
        )

        if self.use_rom:
            self.msg(self._format_rom(data))
        else:
            header = f"|Y[ NPC STATS: {data.get('key', 'Unknown')} ]|n"
            self.msg(header)
            self.msg(str(table))


class CmdMCreate(Command):
    """
    Create a new NPC prototype.

    The prototype is stored in ``world/prototypes/npcs.json`` and does not
    affect any already spawned NPCs. Use ``@editnpc`` later if you need to
    update a live NPC from the saved prototype.

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
        from utils import vnum_registry

        proto["key"] = self.new_key
        area = self.caller.location.db.area if self.caller.location else None
        if area:
            try:
                proto["vnum"] = vnum_registry.get_next_vnum_for_area(
                    area,
                    "npc",
                    builder=self.caller.key,
                )
            except Exception:
                rng = get_area_vnum_range(area)
                if rng:
                    self.msg(f"Using global range. {area} uses {rng[0]}-{rng[1]}.")
                proto["vnum"] = vnum_registry.get_next_vnum("npc")
        prototypes.register_npc_prototype(self.new_key, proto)
        self.msg(f"Prototype {self.new_key} created.")


class CmdMSet(Command):
    """
    Edit a field on an NPC prototype.

    Changes are written to ``world/prototypes/npcs.json``. Existing NPCs are
    unaffected until you apply the prototype with ``@editnpc``.

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
        "npc_type": lambda s: NPC_CLASSES.from_str(s).value,
        "actflags": lambda s: [f.value for f in parse_flag_list(s, ACTFLAGS)],
        "affected_by": lambda s: [f.value for f in parse_flag_list(s, AFFECTED_BY)],
        "languages": lambda s: [f.value for f in parse_flag_list(s, LANGUAGES)],
        "bodyparts": lambda s: [f.value for f in parse_flag_list(s, BODYPARTS)],
        "saving_throws": lambda s: [f.value for f in parse_flag_list(s, SAVING_THROWS)],
        "resistances": lambda s: [f.value for f in parse_flag_list(s, RIS_TYPES)],
        "attack_types": lambda s: [f.value for f in parse_flag_list(s, ATTACK_TYPES)],
        "defense_types": lambda s: [f.value for f in parse_flag_list(s, DEFENSE_TYPES)],
        "skills": lambda s: [p.strip() for p in s.split(",") if p.strip()],
        "spells": lambda s: [p.strip() for p in s.split(",") if p.strip()],
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
    does not alter any existing NPCs. Use ``@editnpc`` if you want to modify a
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
        extra = load_all_prototypes("npc")
        for vnum, proto in extra.items():
            key = proto.get("key", f"mob_{vnum}")
            pdata = dict(proto)
            pdata["vnum"] = vnum
            all_reg[key] = pdata
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

        spawn_entries = ServerConfig.objects.conf("spawn_registry", default=list)
        spawn_lookup: dict[str, list[int]] = {}
        for entry in spawn_entries:
            proto_val = str(entry.get("proto"))
            room_val = entry.get("room")
            if proto_val and room_val is not None:
                spawn_lookup.setdefault(proto_val, []).append(int(room_val))

        if not keys:
            self.msg("No prototypes found.")
            return

        mob_db = get_mobdb()
        vnum_lookup = {}
        finalized_lookup = {}
        for vnum, data in mob_db.db.vnums.items():
            pkey = data.get("proto_key") or data.get("prototype_key") or data.get("key")
            if pkey:
                vnum_lookup[pkey] = vnum
                finalized_lookup[pkey] = vnum
        for vnum, proto in extra.items():
            key = proto.get("key", f"mob_{vnum}")
            vnum_lookup[key] = vnum

        table = evtable.EvTable(
            "VNUM",
            "Key",
            "Area",
            "Status",
            "Lvl",
            "Class",
            "Primary",
            "Roles",
            "Count",
            "Spawn Rooms",
            border="cells",
        )
        for key in keys:
            proto = registry.get(key)
            if not proto:
                continue
            roles = proto.get("roles") or []
            if isinstance(roles, str):
                roles = [roles]
            vnum = (
                vnum_lookup.get(key)
                or vnum_lookup.get(proto.get("key"))
                or proto.get("vnum")
            )
            finalized = False
            if vnum is not None and str(vnum) in mob_db.db.vnums:
                finalized = True
            elif key in finalized_lookup or proto.get("key") in finalized_lookup:
                finalized = True
            status = "yes" if finalized else "no"
            primary = roles[0] if roles else "-"
            area_val = proto.get("area")
            if not area_val:
                for ar in get_areas():
                    if key in area_npcs.get_area_npc_list(ar.key):
                        area_val = ar.key
                        break
            if not area_val and vnum is not None:
                for ar in get_areas():
                    if ar.start <= int(vnum) <= ar.end:
                        area_val = ar.key
                        break
            rooms = list(spawn_lookup.get(str(key), []))
            if vnum is not None:
                rooms += spawn_lookup.get(str(vnum), [])
            room_str = ", ".join(str(r) for r in sorted(set(rooms))) if rooms else "-"
            table.add_row(
                str(vnum) if vnum is not None else "-",
                key,
                area_val or "-",
                status,
                str(proto.get("level", "-")),
                proto.get("npc_type", "-"),
                primary,
                ", ".join(roles) if roles else "-",
                str(counts.get(key, 0)),
                room_str,
            )

        lines = [str(table)]
        if not (area or filter_by or rangestr or show_room or show_area):
            finalized = sorted(str(v) for v in mob_db.db.vnums)
            lines.append("\n|wFinalized VNUMs|n")
            if finalized:
                lines.append(", ".join(str(v) for v in finalized))
            else:
                lines.append("None")

        self.msg("\n".join(lines))


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


class CmdMobExport(Command):
    """Export an NPC prototype to a JSON file."""

    key = "@mobexport"
    locks = "cmd:perm(Builder) or perm(Admin) or perm(Developer)"
    help_category = "Building"

    def parse(self):
        parts = self.args.strip().split(None, 1)
        if len(parts) == 2:
            self.proto_key, self.filename = parts
        else:
            self.proto_key = self.filename = None

    def func(self):
        if not self.proto_key or not self.filename:
            self.msg("Usage: @mobexport <proto> <file>")
            return
        proto = prototypes.get_npc_prototypes().get(self.proto_key)
        if not proto:
            self.msg("Prototype not found.")
            return
        export_dir = Path(settings.PROTOTYPE_NPC_EXPORT_DIR).resolve()
        export_dir.mkdir(parents=True, exist_ok=True)
        fname = Path(self.filename).name
        if not fname.endswith(".json"):
            fname += ".json"
        path = (export_dir / fname).resolve()
        if export_dir != path.parent:
            self.msg("Invalid file path.")
            return
        try:
            with path.open("w") as f:
                json.dump(proto, f, indent=4)
        except OSError:
            self.msg("Unable to write file.")
            return
        self.msg(f"Prototype {self.proto_key} exported to {fname}.")


class CmdMobImport(Command):
    """Import an NPC prototype from a JSON file."""

    key = "@mobimport"
    locks = "cmd:perm(Builder) or perm(Admin) or perm(Developer)"
    help_category = "Building"

    def func(self):
        filename = self.args.strip()
        if not filename:
            self.msg("Usage: @mobimport <file>")
            return
        export_dir = Path(settings.PROTOTYPE_NPC_EXPORT_DIR).resolve()
        fname = Path(filename).name
        if not fname.endswith(".json"):
            fname += ".json"
        path = (export_dir / fname).resolve()
        if export_dir != path.parent or not path.exists():
            self.msg("File not found.")
            return
        try:
            with path.open("r") as f:
                data = json.load(f)
        except json.JSONDecodeError:
            self.msg("Invalid JSON data.")
            return
        key = data.get("key")
        if not key:
            self.msg("Prototype missing 'key' field.")
            return
        prototypes.register_npc_prototype(key, data)
        self.msg(f"Prototype {key} imported.")



class CmdProtoEdit(Command):
    """Edit fields on a numbered mob prototype or display its summary.

    The ``@medit`` alias is kept for backward compatibility but is
    deprecated in favor of ``@protoedit``.
    """

    key = "@protoedit"
    aliases = ["@medit"]
    locks = "cmd:perm(Builder) or perm(Admin) or perm(Developer)"
    help_category = "Building"

    _FIELD_CASTS = {
        "level": int,
        "race": lambda s: NPC_RACES.from_str(s).value,
        "npc_type": lambda s: NPC_CLASSES.from_str(s).value,
        "actflags": lambda s: [f.value for f in parse_flag_list(s, ACTFLAGS)],
        "affected_by": lambda s: [f.value for f in parse_flag_list(s, AFFECTED_BY)],
        "languages": lambda s: [f.value for f in parse_flag_list(s, LANGUAGES)],
        "bodyparts": lambda s: [f.value for f in parse_flag_list(s, BODYPARTS)],
        "saving_throws": lambda s: [f.value for f in parse_flag_list(s, SAVING_THROWS)],
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
        if parts and parts[0].isdigit():
            self.vnum = int(parts[0])
            if len(parts) >= 3:
                self.field = parts[1]
                self.value = " ".join(parts[2:])
            else:
                self.field = self.value = None
        else:
            self.vnum = None
            self.field = self.value = None

    def func(self):
        from utils.mob_proto import get_prototype, register_prototype

        if self.vnum is None:
            self.msg("Usage: @protoedit <vnum> [<field> <value>]")
            return

        proto = get_prototype(self.vnum)
        if not proto:
            self.msg("Prototype not found.")
            return

        if not self.field:
            self.msg(npc_builder.format_mob_summary(proto))
            self.msg(f"Edit with: @protoedit {self.vnum} <field> <value>")
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
        area = find_area_by_vnum(self.vnum)
        if area and "area" not in proto:
            proto["area"] = area.key
        register_prototype(proto, vnum=self.vnum, area=area.key if area else None)
        self.msg(f"{self.field} updated on {self.vnum}.")
