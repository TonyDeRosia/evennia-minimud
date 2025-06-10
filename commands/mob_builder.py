"""Wrapper commands for legacy mob builder functionality."""

from evennia.utils.evmenu import EvMenu
from evennia.prototypes import spawner
from world import prototypes
from typeclasses.characters import NPC
from . import npc_builder

from .command import Command
from .mob_builder_commands import CmdMStat as _OldMStat, CmdMList as _OldMList


class CmdMobBuilder(Command):
    """Launch the unified NPC builder for mob prototypes."""

    key = "mobbuilder"
    locks = "cmd:perm(Builder)"
    help_category = "Building"

    def func(self):
        self.caller.ndb.buildnpc = {
            "triggers": {},
            "npc_class": "base",
            "roles": [],
            "skills": [],
            "spells": [],
            "ris": [],
            "merchant_markup": 1.0,
            "script": "",
            "use_mob": True,
        }
        EvMenu(self.caller, "commands.npc_builder", startnode="menunode_key")


class CmdMSpawn(Command):
    """
    Spawn a mob prototype.

    Prototypes are loaded from ``world/prototypes/npcs.json``. Spawning creates
    a new NPC and leaves any existing ones unchanged. Use ``@medit`` to modify
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
        key = self.args.strip()
        if not key:
            self.msg("Usage: @mspawn <prototype>")
            return
        registry = prototypes.get_npc_prototypes()
        proto = registry.get(key) or registry.get(f"mob_{key}")
        if not proto:
            self.msg("Prototype not found.")
            return
        tclass_path = npc_builder.NPC_CLASS_MAP.get(
            proto.get("npc_class", "base"), "typeclasses.npcs.BaseNPC"
        )
        proto = dict(proto)
        proto.setdefault("typeclass", tclass_path)
        obj = spawner.spawn(proto)[0]
        obj.move_to(self.caller.location, quiet=True)
        self.msg(f"Spawned {obj.key}.")


class CmdMStat(_OldMStat):
    pass


class CmdMList(_OldMList):
    pass


class CmdMedit(Command):
    """Edit an NPC and optionally update its prototype."""

    key = "@medit"
    locks = "cmd:perm(Builder)"
    help_category = "Building"

    def func(self):
        if not self.args:
            self.msg("Usage: @medit <npc>")
            return
        npc = self.caller.search(self.args.strip(), global_search=True)
        if not npc or not npc.is_typeclass(NPC, exact=False):
            self.msg("Invalid NPC.")
            return
        data = npc_builder._gather_npc_data(npc)
        self.caller.ndb.buildnpc = data
        EvMenu(self.caller, "commands.npc_builder", startnode="menunode_desc")


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
