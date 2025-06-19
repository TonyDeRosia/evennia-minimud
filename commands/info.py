from evennia import CmdSet, create_object
from evennia.utils.evtable import EvTable
from evennia.utils import iter_to_str
from utils.currency import to_copper, from_copper, COIN_VALUES
from evennia.contrib.game_systems.clothing.clothing import get_worn_clothes
from world.stats import CORE_STAT_KEYS
from utils.stats_utils import get_display_scroll, _strip_colors, _pad
from utils.slots import SLOT_ORDER

# Mapping of canonical equipment slot keys to the labels shown to players.
SLOT_LABELS = {
    "twohanded": "Twohanded",
    "mainhand": "Mainhand",
    "offhand": "Offhand",
    "head": "Head",
    "neck": "Neck",
    "shoulders": "Shoulders",
    "chest": "Chest",
    "cloak": "Cloak",
    "wrists": "Wrists",
    "hands": "Hands",
    "ring1": "Ring1",
    "ring2": "Ring2",
    "tabard": "Tabard",
    "waist": "Waist",
    "legs": "Legs",
    "feet": "Feet",
    "accessory": "Accessory",
    "trinket": "Trinket",
}


def is_gettable(obj, caller):
    """Return True if caller can pick up obj."""
    return obj.access(caller, "get") and obj.db.gettable is not False


# Canonical equipment slot order for displaying items.  This mirrors the
# ordering used when building ``Character.equipment``.
EQUIPMENT_SLOTS = SLOT_ORDER


def render_equipment(caller):
    """Return formatted equipment display for caller."""
    # use the Character.equipment property to include both worn and wielded
    # items.  Tests can still manipulate caller.db.equipment directly since the
    # property merges those values.
    eq = caller.equipment
    display = ["+=========================+", "| [ EQUIPMENT ]"]

    main = eq.get("mainhand")
    off = eq.get("offhand")
    show_twohanded = (
        main
        and main == off
        and getattr(getattr(main, "db", None), "slot", None) == "twohanded"
    )

    for slot in EQUIPMENT_SLOTS:
        if slot == "twohanded":
            if not show_twohanded:
                continue
            item = main
        elif slot == "mainhand":
            if show_twohanded:
                continue
            item = main
        elif slot == "offhand":
            if show_twohanded:
                continue
            item = off
        else:
            item = eq.get(slot)

        name = item.get_display_name(caller) if item else "NOTHING"
        label = SLOT_LABELS.get(slot, slot.capitalize())
        display.append(f"| {label:<10}: {name}")

    display.append("+=========================+")
    return "\n".join(display)

from .command import Command


class CmdScore(Command):
    """
    View your character sheet. Usage: score

    Usage:
        score

    See |whelp score|n for details.
    """

    key = "score"
    aliases = ("sheet", "sc")
    help_category = "General"

    def func(self):
        self.caller.msg(get_display_scroll(self.caller))


class CmdDesc(Command):
    """
    View or set your description. Usage: desc [text]

    Usage:
        desc

    See |whelp desc|n for details.
    """

    key = "desc"
    help_category = "General"

    def func(self):
        if not self.args:
            desc = self.caller.db.desc or "You have no description."
            self.msg(desc)
        else:
            self.caller.db.desc = self.args.strip()
            self.msg("Description updated.")


class CmdFinger(Command):
    """
    Show information about a player. Usage: finger <player>

    Usage:
        finger

    See |whelp finger|n for details.
    """

    key = "finger"
    aliases = ("whois",)
    help_category = "General"

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
            gp_map = target.db.guild_points or {}
            points = gp_map.get(guild, 0)
            rank = target.db.guild_rank or ""
            lines.append(f"Guild: {guild} ({rank})")
            lines.append(f"Guild Points: {points}")

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
    """
    Place a bounty on another character. Usage: bounty <target> <amount>

    Usage:
        bounty

    See |whelp bounty|n for details.
    """

    key = "bounty"
    help_category = "General"

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
            self.msg("You do not have enough coins to place this bounty.")
            return

        self.caller.db.coins = from_copper(to_copper(wallet) - amount)
        target.db.bounty = (target.db.bounty or 0) + amount
        self.msg(
            f"You place a bounty of {amount} coins on {target.get_display_name(self.caller)}."
        )


class CmdInventory(Command):
    """
    List items you are carrying. Usage: inventory [filter]

    Usage:
        inventory

    See |whelp inventory|n for details.
    """

    key = "inventory"
    aliases = ("inv", "i")
    help_category = "General"

    def func(self):
        caller = self.caller
        items = [obj for obj in caller.contents if not obj.db.worn and is_gettable(obj, caller)]
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


class CmdDropAll(Command):
    """Drop everything you are carrying."""

    key = "drop all"
    aliases = ("dropall",)
    help_category = "General"

    def func(self):
        caller = self.caller
        items = [obj for obj in list(caller.contents) if not obj.db.worn]
        if not items:
            caller.msg("You have nothing to drop.")
            return
        for obj in items:
            obj.move_to(caller.location, quiet=True, move_type="drop")
            obj.at_drop(caller)
        caller.update_carry_weight()
        caller.msg("You drop everything you are carrying.")


class CmdDrop(Command):
    """Drop an item or a number of coins."""

    key = "drop"
    aliases = ("discard", "throw")
    help_category = "General"

    def func(self):
        caller = self.caller
        if not self.args:
            caller.msg("Drop what?")
            return

        parts = self.args.strip().split()
        if len(parts) == 2 and parts[0].isdigit() and parts[1].lower() in COIN_VALUES:
            amount = int(parts[0])
            ctype = parts[1].lower()
            wallet = caller.db.coins or {}
            if amount <= 0 or wallet.get(ctype, 0) < amount:
                caller.msg("You don't have that many coins.")
                return
            wallet[ctype] -= amount
            caller.db.coins = wallet
            coin = create_object(
                "typeclasses.objects.CoinPile",
                key=f"{ctype} coins",
                location=caller.location,
            )
            coin.db.coin_type = ctype
            coin.db.amount = amount
            coin.db.from_pouch = True
            caller.msg(f"You drop {amount} {ctype} coin{'s' if amount != 1 else ''}.")
            return

        obj = caller.search(self.args, location=caller)
        if not obj:
            return
        obj.move_to(caller.location, quiet=True, move_type="drop")
        obj.at_drop(caller)
        caller.update_carry_weight()
        caller.msg(f"You drop {obj.get_display_name(caller)}.")


class CmdGive(Command):
    """Give an item or coins to someone."""

    key = "give"
    help_category = "General"

    def parse(self):
        if "=" in self.args:
            lhs, rhs = self.args.split("=", 1)
            self.lhs = lhs.strip()
            self.rhs = rhs.strip()
        else:
            parts = self.args.split()
            if len(parts) >= 2:
                self.lhs = " ".join(parts[:-1])
                self.rhs = parts[-1]
            else:
                self.lhs = self.args.strip()
                self.rhs = ""

    def func(self):
        caller = self.caller
        if not self.lhs or not self.rhs:
            caller.msg("Give <item|amount coin> <target>")
            return

        target = caller.search(self.rhs)
        if not target:
            return

        parts = self.lhs.split()
        if len(parts) == 2 and parts[0].isdigit() and parts[1].lower() in COIN_VALUES:
            amount = int(parts[0])
            ctype = parts[1].lower()
            wallet = caller.db.coins or {}
            if amount <= 0 or wallet.get(ctype, 0) < amount:
                caller.msg("You don't have that many coins.")
                return
            wallet[ctype] -= amount
            caller.db.coins = wallet
            coin = create_object(
                "typeclasses.objects.CoinPile",
                key=f"{ctype} coins",
                location=caller.location,
            )
            coin.db.coin_type = ctype
            coin.db.amount = amount
            coin.db.from_pouch = True
            coin.move_to(target, quiet=True)
            caller.msg(
                f"You give {amount} {ctype} coin{'s' if amount != 1 else ''} to {target.get_display_name(caller)}."
            )
            target.msg(
                f"{caller.get_display_name(target)} gives you {amount} {ctype} coin{'s' if amount != 1 else ''}."
            )
            return

        obj = caller.search(self.lhs, location=caller)
        if not obj:
            caller.msg("You aren't carrying that.")
            return
        if obj.move_to(target, quiet=True, move_type="give"):
            obj.at_get(target)
        caller.update_carry_weight()
        caller.msg(f"You give {obj.get_display_name(caller)} to {target.get_display_name(caller)}.")
        target.msg(f"{caller.get_display_name(target)} gives you {obj.get_display_name(target)}.")


class CmdGetAll(Command):
    """Pick up everything in the room."""

    key = "get all"
    aliases = ("getall",)
    help_category = "General"

    def func(self):
        caller = self.caller
        location = caller.location
        if not location:
            caller.msg("You cannot pick anything up.")
            return
        items = [
            obj
            for obj in location.contents
            if is_gettable(obj, caller) and obj != caller
        ]
        if not items:
            caller.msg("There is nothing here to pick up.")
            return
        for obj in items:
            if obj.move_to(caller, quiet=True, move_type="get"):
                obj.at_get(caller)
        caller.update_carry_weight()
        caller.msg("You pick up everything you can.")


class CmdGetAllCorpse(Command):
    """Pick up all corpses in the room."""

    key = "get all corpse"
    help_category = "General"

    def func(self):
        caller = self.caller
        location = caller.location
        if not location:
            caller.msg("You cannot pick anything up.")
            return
        corpses = [
            obj for obj in location.contents if getattr(obj.db, "is_corpse", False)
        ]
        if not corpses:
            caller.msg("There are no corpses here.")
            return
        for obj in corpses:
            if obj.move_to(caller, quiet=True, move_type="get"):
                obj.at_get(caller)
        caller.update_carry_weight()
        caller.msg("You gather the corpses.")


class CmdEquipment(Command):
    """
    Show what you are wearing and wielding. Usage: equipment

    Usage:
        equipment

    See |whelp equipment|n for details.
    """

    key = "equipment"
    aliases = ("eq",)
    help_category = "General"

    def func(self):
        self.msg(render_equipment(self.caller))


class CmdInspect(Command):
    """
    Examine an item for more information.

    Usage:
        inspect <item>

    See |whelp inspect|n for details.
    """

    key = "inspect"
    help_category = "General"

    def func(self):
        caller = self.caller
        if not self.args:
            caller.msg("Usage: inspect <item>")
            return

        query = self.args.strip()
        matches = caller.search(query, quiet=True)
        obj = None
        if matches:
            if isinstance(matches, list):
                if len(matches) == 1:
                    obj = matches[0]
                else:
                    ql = query.lower()
                    exact = [
                        o
                        for o in matches
                        if o.key.lower() == ql
                        or ql in [al.lower() for al in o.aliases.all()]
                    ]
                    if len(exact) == 1:
                        obj = exact[0]
            else:
                obj = matches
        if not obj:
            obj = caller.search(query)
            if not obj:
                return

        lines = [f"|w{obj.key}|n"]
        desc = obj.db.desc or "You see nothing special."
        lines.append(desc)

        mods = (
            getattr(obj.db, "bonuses", None)
            or getattr(obj.db, "stat_mods", None)
            or getattr(obj.db, "modifiers", None)
        )
        if mods:
            lines.append("Bonuses:")
            for stat, amt in mods.items():
                label = stat.replace("_", " ")
                if stat.isupper():
                    label = stat.upper()
                else:
                    label = label.title()
                lines.append(f"  {label} {amt:+d}")

        armor = getattr(obj.db, "armor", 0)
        if armor:
            lines.append(f"  Armor +{armor}")

        req = obj.db.required_perception_to_identify
        if obj.tags.has("unidentified") and req is not None:
            from world.system import stat_manager
            per = stat_manager.get_effective_stat(caller, "perception")
            if per >= req:
                obj.tags.remove("unidentified")
                obj.db.identified = True

        is_admin = caller.check_permstring("Admin") or caller.check_permstring("Builder")

        if obj.db.identified or is_admin:
            width = max(
                len(label)
                for label in [
                    "Slot",
                    "Damage",
                    "Buffs",
                    "Flags",
                    "Weight",
                    "Identified",
                    "Type",
                    "Sated Boost",
                ]
            )
            lines.append("")
            lines.append("|Y[ ITEM INFO ]|n")

            def add(label, value):
                lines.append(f"|c{label.ljust(width)}|n: {value}")

            slot = obj.db.slot or obj.db.clothing_type
            if slot:
                add("Slot", slot)

            dmg = obj.db.damage_dice or obj.db.dmg
            if dmg is not None:
                dtype = None
                dtypes = obj.tags.get(category="damage_type", return_list=True)
                if dtypes:
                    dtype = dtypes[0]
                dmg_val = f"{dmg}"
                if dtype:
                    dmg_val += f" ({dtype})"
                add("Damage", dmg_val)

            effects = obj.tags.get(category="buff", return_list=True) or []
            import re

            pattern = re.compile(r"[A-Z]+[+-]\d+")
            effects.extend(t for t in obj.tags.all() if pattern.fullmatch(str(t)))
            if obj.db.buff:
                effects.append(str(obj.db.buff))
            if effects:
                add("Buffs", ", ".join(sorted(set(effects))))

            flags = obj.tags.get(category="flag", return_list=True) or []
            if flags:
                add("Flags", ", ".join(sorted(flags)))

            if (weight := obj.db.weight) is not None:
                add("Weight", weight)

            if (itype := getattr(obj.db, "item_type", None) or getattr(obj.db, "type", None)):
                add("Type", str(itype).capitalize())

            boost = (
                getattr(obj.db, "sated_boost", None)
                if hasattr(obj.db, "sated_boost")
                else getattr(obj.db, "sated", None)
            )
            if boost is not None:
                add("Sated Boost", f"+{boost}")

            add("Identified", "yes" if obj.db.identified else "no")

        caller.msg("\n".join(lines))


class CmdBuffs(Command):
    """
    Display active buff effects. Usage: buffs

    Usage:
        buffs

    See |whelp buffs|n for details.
    """

    key = "buffs"
    help_category = "General"

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
    """
    View your active buffs and status effects.

    Usage:
        affects

    See |whelp affects|n for details.
    """

    key = "affects"
    aliases = ("effects", "aff")
    help_category = "General"

    def func(self):
        from world.effects import EFFECTS

        caller = self.caller
        rows = []

        cd_lines = []
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

        for key in caller.cooldowns.all:
            remaining = caller.cooldowns.time_left(key, use_int=True)
            if remaining:
                cd_lines.append(f"|C{key.capitalize()}|n - |cCD|n {remaining} Seconds")

        if not rows and not cd_lines:
            self.msg("You are not affected by any effects.")
            return

        table = EvTable(
            "|wName|n", "|wDuration|n", "|wDescription|n", border="none", align="l"
        )
        for name, dur, desc in rows:
            table.add_row(name, str(dur) if dur is not None else "-", desc)
        output = str(table)
        if cd_lines:
            output += "\n" + "\n".join(cd_lines)
        self.msg(output)


class CmdTitle(Command):
    """
    View or change your title. Usage: title [new title]

    Usage:
        title

    See |whelp title|n for details.
    """

    key = "title"
    help_category = "General"

    def func(self):
        if not self.args:
            title = self.caller.db.title or "You have no title."
            self.msg(title)
        else:
            self.caller.db.title = self.args.strip()
            self.msg("Title updated.")


class CmdPrompt(Command):
    """
    Customize the information shown in your command prompt.

    Usage:
        prompt

    See |whelp prompt|n for details.
    """

    key = "prompt"
    help_category = "General"

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


class CmdReport(Command):
    """Broadcast your status to the room."""

    key = "report"
    help_category = "General"

    def func(self):
        prompt = self.caller.get_display_status(self.caller)
        location = self.caller.location
        if location:
            location.msg_contents(
                f"{self.caller.key} reports:\n{prompt}", exclude=self.caller
            )
        self.caller.msg("|gYou report your current status.|n")


class CmdScan(Command):
    """
    Look around and into adjacent rooms.

    Usage:
        scan

    See |whelp scan|n for details.
    """

    key = "scan"
    help_category = "Movement"

    def func(self):
        caller = self.caller
        location = caller.location
        if not location:
            caller.msg("You have no location.")
            return

        is_admin = caller.check_permstring("Admin")

        out = [location.return_appearance(caller)]

        for ex in location.exits:
            if not ex.access(caller, "view"):
                continue
            dest = ex.destination
            if not dest or not dest.access(caller, "view"):
                continue

            lines = [f"|c{ex.key.capitalize()}|n -> {dest.key}"]
            lines.append(dest.db.desc or "You see nothing special.")

            if is_admin:
                flags = dest.tags.get(category="room_flag", return_list=True) or []
                if flags:
                    lines.append("Room flags: " + ", ".join(sorted(flags)))
                tags = dest.tags.get(return_list=True) or []
                if tags:
                    lines.append("Tags: " + ", ".join(sorted(tags)))

            chars = []
            things = []
            for obj in dest.contents:
                if obj.destination:
                    continue
                if not is_admin and not obj.access(caller, "view"):
                    continue

                name = obj.get_display_name(caller)
                if "character" in obj._content_types:
                    if is_admin:
                        try:
                            hp = int(obj.traits.health.current)
                            mp = int(obj.traits.mana.current)
                            sp = int(obj.traits.stamina.current)
                            name += f" (HP {hp}/{int(obj.traits.health.max)}, MP {mp}/{int(obj.traits.mana.max)}, SP {sp}/{int(obj.traits.stamina.max)})"
                        except Exception:
                            pass
                    chars.append(name)
                else:
                    things.append(name)

            if chars:
                lines.append("|wCharacters:|n " + ", ".join(chars))
            if things:
                lines.append("|wYou see:|n " + ", ".join(things))

            exits = [e.key.capitalize() for e in dest.exits if is_admin or e.access(caller, "view")]
            lines.append("|wExits:|n " + (", ".join(exits) if exits else "None"))

            out.append("\n".join(lines))

        caller.msg("\n\n".join(out))


class InfoCmdSet(CmdSet):
    key = "Info CmdSet"

    def at_cmdset_creation(self):
        super().at_cmdset_creation()
        self.add(CmdScore)
        self.add(CmdDesc)
        self.add(CmdFinger)
        self.add(CmdBounty)
        self.add(CmdInventory)
        self.add(CmdDrop)
        self.add(CmdGive)
        self.add(CmdGetAll)
        self.add(CmdGetAllCorpse)
        self.add(CmdDropAll)
        self.add(CmdInspect)
        self.add(CmdEquipment)
        self.add(CmdAffects)
        self.add(CmdBuffs)
        self.add(CmdTitle)
        self.add(CmdPrompt)
        self.add(CmdReport)
        self.add(CmdScan)
