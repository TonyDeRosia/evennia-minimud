from evennia import CmdSet
from evennia.utils.evtable import EvTable
from evennia.utils import iter_to_str
from utils.currency import to_copper, from_copper
from evennia.contrib.game_systems.clothing.clothing import get_worn_clothes
from world.guilds import get_rank_title
from world.stats import CORE_STAT_KEYS
from utils.stats_utils import get_display_scroll, _strip_colors, _pad

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
        # gather lines of information
        lines = []
        title = target.db.title or ""
        if title:
            lines.append(f"|w{target.key}|n - {title}")
        else:
            lines.append(f"|w{target.key}|n")

        desc = target.db.desc or "They have no description."

        race = target.db.race or "Unknown"
        charclass = target.db.charclass or "Unknown"
        lines.append(f"Race: {race}")
        lines.append(f"Class: {charclass}")

        if guild := target.db.guild:
            honor = target.db.guild_honor or 0
            rank = get_rank_title(guild, honor)
            lines.append(f"Guild: {guild} ({rank})")
            lines.append(f"Honor: {honor}")

        bounty = target.attributes.get("bounty", 0)
        if bounty:
            lines.append(f"Bounty: {bounty}")
        else:
            lines.append("No bounty.")

        lines.append("")
        lines.extend(desc.splitlines() or ["They have no description."])

        width = max(len(_strip_colors(l)) for l in lines)
        top = "+" + "=" * (width + 2) + "+"
        bottom = "+" + "=" * (width + 2) + "+"
        boxed = [top] + [f"| " + _pad(l, width) + " |" for l in lines] + [bottom]
        self.msg("\n".join(boxed))


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

        wallet = self.caller.db.coins or {}
        if to_copper(wallet) < amount:
            self.msg("You don't have that many coins.")
            return
        self.caller.db.coins = from_copper(to_copper(wallet) - amount)
        target.db.bounty = (target.db.bounty or 0) + amount
        self.msg(
            f"You place a bounty of {amount} coins on {target.get_display_name(self.caller)}."
        )


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
        caller.update_carry_weight()
        weight = caller.db.carry_weight or 0
        capacity = caller.db.carry_capacity or 0
        enc = caller.encumbrance_level()
        line = f"Carry Weight: {weight} / {capacity}"
        if enc:
            line += f"  {enc}"
        caller.msg(line)


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
    """List active buff effects."""

    key = "buffs"
    help_category = "general"

    def func(self):
        from world.effects import EFFECTS

        caller = self.caller
        rows = []

        for tag in caller.tags.get(category="buff", return_list=True):
            effect = EFFECTS.get(tag)
            if effect and effect.type != "buff":
                continue
            name = effect.name if effect else tag
            desc = effect.desc if effect else ""
            dur = (
                caller.db.status_effects.get(tag) if caller.db.status_effects else None
            )
            rows.append((name, dur, desc))

        for stat, entries in (caller.db.temp_bonuses or {}).items():
            effect = EFFECTS.get(stat)
            if effect and effect.type != "buff":
                continue
            for entry in entries:
                name = effect.name if effect else f"{stat.capitalize()} Bonus"
                desc = effect.desc if effect else f"Temporary bonus to {stat}."
                rows.append((name, entry.get("duration"), desc))

        if not rows:
            self.msg("You have no active effects.")
            return

        table = EvTable(
            "|wName|n", "|wDuration|n", "|wDescription|n", border="none", align="l"
        )
        for name, dur, desc in rows:
            table.add_row(name, str(dur) if dur is not None else "-", desc)
        self.msg(str(table))


class CmdAffects(Command):
    """List all active effects."""

    key = "affects"
    aliases = ("effects",)
    help_category = "general"

    def func(self):
        from world.effects import EFFECTS

        caller = self.caller
        rows = []

        for status, dur in (caller.db.status_effects or {}).items():
            effect = EFFECTS.get(status)
            name = effect.name if effect else status
            desc = effect.desc if effect else ""
            rows.append((name, dur, desc))

        for tag in caller.tags.get(category="buff", return_list=True):
            effect = EFFECTS.get(tag)
            name = effect.name if effect else tag
            desc = effect.desc if effect else ""
            dur = (
                caller.db.status_effects.get(tag) if caller.db.status_effects else None
            )
            rows.append((name, dur, desc))

        for stat, entries in (caller.db.temp_bonuses or {}).items():
            for entry in entries:
                ekey = entry.get("key") or stat
                effect = EFFECTS.get(ekey) or EFFECTS.get(stat)
                if effect:
                    name = effect.name
                    desc = effect.desc
                else:
                    name = ekey if entry.get("key") else f"{stat.capitalize()} Bonus"
                    desc = f"Temporary bonus to {stat}."
                rows.append((name, entry.get("duration"), desc))

        if not rows:
            self.msg("You are not affected by any effects.")
            return

        table = EvTable(
            "|wName|n", "|wDuration|n", "|wDescription|n", border="none", align="l"
        )
        for name, dur, desc in rows:
            table.add_row(name, str(dur) if dur is not None else "-", desc)
        self.msg(str(table))


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


class CmdPrompt(Command):
    """View or set your command prompt."""

    key = "prompt"
    help_category = "general"

    def func(self):
        caller = self.caller
        if not self.args:
            current = caller.db.prompt_format or caller.get_resource_prompt()
            caller.msg(f"Current prompt: {current}")
            caller.msg("Set a new prompt with |wprompt <format>|n.")
            return
        caller.db.prompt_format = self.args.strip()
        caller.msg("Prompt updated.")
        caller.refresh_prompt()


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
        self.add(CmdAffects)
        self.add(CmdBuffs)
        self.add(CmdTitle)
        self.add(CmdPrompt)
