from evennia import create_object
from evennia.utils.search import search_object
from typeclasses.npcs import BaseNPC
from evennia.utils import evtable
from .command import Command
from . import npc_builder
from world import prototypes, area_npcs

class CmdMStat(Command):
    """Inspect an NPC's stats."""

    key = "@mstat"
    locks = "cmd:perm(Builder) or perm(Admin) or perm(Developer)"
    help_category = "Building"

    def func(self):
        if not self.args:
            self.msg("Usage: @mstat <npc>")
            return
        target = self.caller.search(self.args.strip(), global_search=True)
        if not target or not target.is_typeclass(BaseNPC, exact=False):
            self.msg("NPC not found.")
            return
        data = npc_builder._gather_npc_data(target)
        table = evtable.EvTable("Attribute", "Value")
        table.add_row("Key", target.key)
        table.add_row("Typeclass", target.typeclass_path)
        table.add_row("Level", data.get("level", 1))
        table.add_row("AI", data.get("ai_type", ""))
        hp = data.get("hp")
        if hp:
            table.add_row("HP", hp)
        stats = data.get("primary_stats") or {}
        if stats:
            statline = ", ".join(f"{k}:{v}" for k, v in stats.items())
            table.add_row("Stats", statline)
        roles = target.tags.get(category="npc_role", return_list=True) or []
        if roles:
            table.add_row("Roles", ", ".join(roles))
        self.msg(str(table))

class CmdMList(Command):
    """List NPC prototypes optionally filtered by area."""

    key = "@mlist"
    locks = "cmd:perm(Builder) or perm(Admin) or perm(Developer)"
    help_category = "Building"

    def func(self):
        area = self.args.strip()
        registry = prototypes.get_npc_prototypes()
        if area:
            keys = area_npcs.get_area_npc_list(area)
            if not keys:
                self.msg("No prototypes registered for that area.")
                return
        else:
            keys = registry.keys()
        lines = []
        for key in keys:
            desc = registry.get(key, {}).get("desc", "")
            lines.append(f"{key} - {desc}" if desc else key)
        if not lines:
            self.msg("No prototypes found.")
        else:
            self.msg("\n".join(lines))
