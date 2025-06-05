from evennia import CmdSet
from evennia.utils.evtable import EvTable
from evennia.utils import iter_to_str
from evennia.contrib.game_systems.clothing.clothing import get_worn_clothes
from world.guilds import get_rank_title
from world.stats import CORE_STAT_KEYS
from utils.stats_utils import get_display_scroll

from .command import Command


class CmdScore(Command):
    """View your character sheet (alias \"sc\")."""

    key = "score"
    aliases = ("sheet", "sc")
    help_category = "general"

    def func(self):
        self.caller.msg(get_display_scroll(self.caller))


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
        if not self.args or self.args.strip().lower() in {"self", "me"}:
            target = self.caller
        else:
            target = self.caller.search(self.args.strip(), global_search=True)
            if not target:
                return
        desc = target.db.desc or "They have no description."
        stat_parts = []
        for key in CORE_STAT_KEYS:
            trait = target.traits.get(key)
            value = trait.value if trait else 0
            stat_parts.append(f"{key} {value}")
        if (per := target.traits.get("perception")):
            stat_parts.append(f"PER {per.value}")
        stats = ", ".join(stat_parts)
        self.msg(f"|w{target.key}|n - {desc}")
        self.msg(stats)
        if guild := target.db.guild:
            honor = target.db.guild_honor or 0
            rank = get_rank_title(guild, honor)
            self.msg(f"Guild: {guild} ({rank})")
            self.msg(f"Honor: {honor}")
        bounty = target.attributes.get("bounty", 0)
        if bounty > 0:
            self.msg(f"Bounty: {bounty}")


class CmdBounty(Command):
    """Place a bounty on another character."""

    key = "bounty"
    help_category = "general"

    def func(self):
        if not self.args:
            self.msg("Usage: bounty <target> <amount>")
            return

        parts = self.args.split(None, 1)
        if len(parts) != 2 or not parts[1].isdigit():
            self.msg("Usage: bounty <target> <amount>")
            return

        target_name, amount_str = parts
        amount = int(amount_str)
        target = self.caller.search(target_name, global_search=True)
        if not target:
            return

        if amount <= 0:
            self.msg("Amount must be positive.")
            return

        coins = self.caller.db.coins or 0
        if coins < amount:
            self.msg("You don't have that many coins.")
            return

        self.caller.db.coins = coins - amount
        target.db.bounty = (target.db.bounty or 0) + amount
        self.msg(f"You place a bounty of {amount} coins on {target.get_display_name(self.caller)}.")


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


class CmdTitle(Command):
    """Set or view your character title."""

    key = "title"
    help_category = "general"

    def func(self):
        if not self.args:
            title = self.caller.db.title or "You have no title."
            self.msg(title)
        else:
            self.caller.db.title = self.args.strip()
            self.msg("Title updated.")


class InfoCmdSet(CmdSet):
    key = "Info CmdSet"

    def at_cmdset_creation(self):
        super().at_cmdset_creation()
        self.add(CmdScore)
        self.add(CmdDesc)
        self.add(CmdFinger)
        self.add(CmdBounty)
        self.add(CmdInventory)
        self.add(CmdEquipment)
        self.add(CmdBuffs)
        self.add(CmdTitle)

