"""Wrapper commands for legacy mob builder functionality."""

from evennia.utils.evmenu import EvMenu
from evennia.prototypes import spawner
from utils.mob_proto import spawn_from_vnum, get_prototype
from utils import vnum_registry
from world.scripts.mob_db import get_mobdb
from evennia.utils import delay
from world import prototypes
from typeclasses.characters import NPC
from . import npc_builder

from .command import Command
from .mob_builder_commands import CmdMStat as _OldMStat, CmdMList as _OldMList


class CmdMSpawn(Command):
    """
    Spawn a mob prototype.

    Prototypes are loaded from ``world/prototypes/npcs.json``. Spawning creates
    a new NPC and leaves any existing ones unchanged. Use ``@editnpc`` to modify
    a live NPC.

    Usage:
        @mspawn <prototype>

    Example:
        @mspawn bandit
    """

    key = "@mspawn"
    locks = "cmd:perm(Builder)"
    help_category = "Building"

    def func(self):
        arg = self.args.strip()
        if not arg:
            self.msg("Usage: @mspawn <prototype>")
            return

        vnum = None
        if arg.isdigit():
            vnum = int(arg)
        elif arg.upper().startswith("M") and arg[1:].isdigit():
            vnum = int(arg[1:])

        if vnum is not None:
            if not vnum_registry.validate_vnum(vnum, "npc") and not get_prototype(vnum):
                self.msg("Invalid VNUM.")
                return
            obj = spawn_from_vnum(vnum, location=self.caller.location)
            if not obj:
                self.msg("Prototype not found.")
                return
        else:
            # look for a vnum prototype matching this key
            mob_db = get_mobdb()
            vmatch = next((num for num, p in mob_db.db.vnums.items() if p.get("key") == arg), None)
            if vmatch is not None:
                obj = spawn_from_vnum(vmatch, location=self.caller.location)
                if not obj:
                    self.msg("Prototype not found.")
                    return
            else:
                registry = prototypes.get_npc_prototypes()
                proto = registry.get(arg) or registry.get(f"mob_{arg}")
                if not proto:
                    self.msg("Prototype not found.")
                    return
                tclass_path = npc_builder.NPC_TYPE_MAP.get(
                    proto.get("npc_type", "base"), "typeclasses.npcs.BaseNPC"
                )
                proto = dict(proto)
                proto.setdefault("typeclass", tclass_path)
                obj = spawner.spawn(proto)[0]
                obj.move_to(self.caller.location, quiet=True)
                if proto.get("vnum"):
                    obj.db.vnum = proto["vnum"]
                    obj.tags.add(f"M{proto['vnum']}", category="vnum")

        self.msg(f"Spawned {obj.key}.")


class CmdMobPreview(Command):
    """
    Spawn a mob prototype briefly for preview.

    The NPC appears in your location and is automatically
    removed after a short delay.

    Usage:
        @mobpreview <prototype>

    Example:
        @mobpreview goblin
    """

    key = "@mobpreview"
    locks = "cmd:perm(Builder)"
    help_category = "Building"

    def func(self):
        key = self.args.strip()
        if not key:
            self.msg("Usage: @mobpreview <prototype>")
            return
        if key.isdigit():
            obj = spawn_from_vnum(int(key), location=self.caller.location)
            if not obj:
                self.msg("Prototype not found.")
                return
        else:
            registry = prototypes.get_npc_prototypes()
            proto = registry.get(key) or registry.get(f"mob_{key}")
            if not proto:
                self.msg("Prototype not found.")
                return
            tclass_path = npc_builder.NPC_TYPE_MAP.get(
                proto.get("npc_type", "base"), "typeclasses.npcs.BaseNPC"
            )
            proto = dict(proto)
            proto.setdefault("typeclass", tclass_path)
            obj = spawner.spawn(proto)[0]
            obj.move_to(self.caller.location, quiet=True)
        delay(30, obj.delete)
        self.msg(f"Previewing {obj.key}. It will vanish soon.")


class CmdMStat(_OldMStat):
    pass


class CmdMList(_OldMList):
    pass



class CmdMobTemplate(Command):
    """Load a predefined mob template into the current build."""

    key = "@mobtemplate"
    locks = "cmd:perm(Builder)"
    help_category = "Building"

    def func(self):
        from world.templates.mob_templates import MOB_TEMPLATES, get_template

        arg = self.args.strip().lower()
        if not arg or arg == "list":
            names = ", ".join(sorted(MOB_TEMPLATES))
            self.msg(f"Available templates: {names}")
            return
        data = get_template(arg)
        if not data:
            self.msg("Unknown template.")
            return
        self.caller.ndb.buildnpc = self.caller.ndb.buildnpc or {}
        self.caller.ndb.buildnpc.update(data)
        self.msg(f"Template '{arg}' loaded into builder.")


class CmdQuickMob(Command):
    """Spawn and register a mob from a template in one step."""

    key = "@quickmob"
    locks = "cmd:perm(Builder)"
    help_category = "Building"

    def func(self):
        from world.templates.mob_templates import get_template
        from utils.mob_utils import assign_next_vnum

        args = self.args.strip()
        if not args:
            self.msg("Usage: @quickmob <key> [template]")
            return

        parts = args.split(None, 1)
        key = parts[0]
        template = parts[1] if len(parts) > 1 else "warrior"

        data = get_template(template)
        if not data:
            self.msg("Unknown template.")
            return

        vnum = assign_next_vnum("npc")

        data = dict(data)
        data.update({"key": key, "vnum": vnum, "use_mob": True})
        self.caller.ndb.buildnpc = data
        npc_builder._create_npc(self.caller, "", register=True)
