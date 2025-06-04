from evennia import CmdSet
from evennia.utils.evtable import EvTable
from evennia.utils import iter_to_str
from evennia.contrib.game_systems.clothing.clothing import get_worn_clothes

from .command import Command


class CmdScore(Command):
    """View your basic stats."""

    key = "score"
    aliases = ("sheet",)
    help_category = "general"

    def func(self):
        caller = self.caller
        stats = []
        for key, disp in (
            ("STR", "STR"),
            ("CON", "CON"),
            ("DEX", "DEX"),
            ("INT", "INT"),
            ("WIS", "WIS"),
            ("LUCK", "LUCK"),
        ):
            trait = caller.traits.get(key)
            base = trait.base if trait else 0
            mod = trait.modifier if trait else 0
            total = base + mod
            text = f"{base}" if not mod else f"{base} ({total})"
            stats.append([disp, text])
        table = EvTable(table=list(zip(*stats)), border="none")
        caller.msg(str(table))


class CmdDesc(Command):
    """View or set your description."""

    key = "desc"
    help_category = "general"

    def func(self):
        if not self.args:
            desc = self.caller.db.desc or "You have no description."
            self.msg(desc)
        else:
            self.caller.db.desc = self.args.strip()
            self.msg("Description updated.")


class CmdFinger(Command):
    """Show information about another player."""

    key = "finger"
    aliases = ("whois",)
    help_category = "general"

    def func(self):
        if not self.args:
            self.msg("Finger whom?")
            return
        target = self.caller.search(self.args.strip(), global_search=True)
        if not target:
            return
        desc = target.db.desc or "They have no description."
        stat_parts = []
        for key, label in (
            ("STR", "STR"),
            ("CON", "CON"),
            ("DEX", "DEX"),
            ("INT", "INT"),
            ("WIS", "WIS"),
            ("LUCK", "LUCK"),
        ):
            trait = target.traits.get(key)
            value = trait.value if trait else 0
            stat_parts.append(f"{label} {value}")
        stats = ", ".join(stat_parts)
        self.msg(f"|w{target.key}|n - {desc}")
        self.msg(stats)


class CmdInventory(Command):
    """List your carried items."""

    key = "inventory"
    aliases = ("inv", "i")
    help_category = "general"

    def func(self):
        caller = self.caller
        items = [obj for obj in caller.contents if not obj.db.worn]
        if self.args:
            filt = self.args.lower()
            items = [obj for obj in items if filt in obj.key.lower()]
        if not items:
            self.msg("You are carrying nothing.")
            return
        table = EvTable(border="none")
        for obj in items:
            table.add_row(obj.get_display_name(caller))
        caller.msg(str(table))


class CmdEquipment(Command):
    """List what you are wearing or wielding."""

    key = "equipment"
    aliases = ("eq",)
    help_category = "general"

    def func(self):
        caller = self.caller
        out = []
        wielded = caller.attributes.get("_wielded", {})
        if wielded:
            wielded.deserialize()
            for hand, weap in wielded.items():
                if weap:
                    out.append(f"{hand.capitalize()}: {weap.get_display_name(caller)}")
        worn = get_worn_clothes(caller)
        if worn:
            worn_list = ", ".join(obj.get_display_name(caller) for obj in worn)
            out.append(f"Worn: {worn_list}")
        if not out:
            self.msg("You have nothing equipped.")
        else:
            for line in out:
                self.msg(line)


class CmdBuffs(Command):
    """List active temporary effects."""

    key = "buffs"
    help_category = "general"

    def func(self):
        buffs = self.caller.tags.get(category="buff", return_list=True)
        if not buffs:
            self.msg("You have no active effects.")
        else:
            self.msg("Active effects: " + iter_to_str(sorted(buffs)))


class InfoCmdSet(CmdSet):
    key = "Info CmdSet"

    def at_cmdset_creation(self):
        super().at_cmdset_creation()
        self.add(CmdScore)
        self.add(CmdDesc)
        self.add(CmdFinger)
        self.add(CmdInventory)
        self.add(CmdEquipment)
        self.add(CmdBuffs)

