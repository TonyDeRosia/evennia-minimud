from evennia import CmdSet, create_object
from evennia.objects.models import ObjectDB
import shlex
import re
from evennia.utils.ansi import strip_ansi
from .command import Command
from .info import CmdScan
from .building import (
    CmdSetDesc,
    CmdSetWeight,
    CmdSetSlot,
    CmdSetDamage,
    CmdSetBuff,
    CmdSetFlag,
    CmdRemoveFlag,
)
from world.stats import CORE_STAT_KEYS, ALL_STATS
from world.system import stat_manager
from world.system.constants import MAX_LEVEL
from utils.stats_utils import get_display_scroll, normalize_stat_key
from utils import VALID_SLOTS, normalize_slot
from .npc_builder import CmdCNPC


def _safe_split(text):
    """Safely split command arguments using ``shlex``.

    Provides a clearer error message when quotes are unbalanced.
    """

    try:
        return shlex.split(text)
    except ValueError:
        raise ValueError("No closing quotation found; enclose multiword names in quotes.")



# Valid stats that can be modified by gear bonuses
VALID_STATS = {normalize_stat_key(stat.key) for stat in ALL_STATS}

# Regular expression for matching stat modifiers like "hp+5" or "Armor Pen+3"
STAT_MOD_RE = re.compile(r"([A-Za-z][A-Za-z _]*?)\+(-?\d+)")


def parse_stat_mods(text):
    """Parse comma-separated stat modifiers from a string.

    Returns a tuple ``(mods, desc)`` where ``mods`` is a dict mapping stat
    keys to integer bonuses and ``desc`` is any remaining description text.

    Raises ``ValueError`` if an unknown stat is encountered.
    """

    bonuses = {}
    desc = None
    if not text:
        return bonuses, desc

    pieces = [p.strip() for p in text.split(",")]
    pattern = STAT_MOD_RE
    desc_parts = []

    for i, piece in enumerate(pieces):
        if not piece:
            continue
        match = pattern.match(piece)
        if match:
            stat_name = match.group(1).strip()
            amount = int(match.group(2))
            key = normalize_stat_key(stat_name)
            if key not in VALID_STATS:
                raise ValueError(stat_name)
            bonuses[key] = amount
            remainder = piece[match.end() :].strip()
            if remainder:
                desc_parts.append(remainder)
                desc_parts.extend(p.strip() for p in pieces[i + 1 :])
                break
        else:
            if "+" in piece:
                raise ValueError(piece)
            desc_parts.append(piece)
            desc_parts.extend(p.strip() for p in pieces[i + 1 :])
            break

    if desc_parts:
        desc = ", ".join(desc_parts).strip()
    if desc is None and text:
        desc = text.strip()
    return bonuses, desc


class CmdSetStat(Command):
    """
    Change a character's stat directly.

    Usage:
        setstat <target> <stat> <value>

    See |whelp setstat|n for details.
    """

    key = "setstat"
    aliases = ("set",)
    locks = "cmd:perm(Admin) or perm(Builder)"
    help_category = "Admin"

    def func(self):
        if not self.args:
            self.msg("Usage: setstat <target> <stat> <value>")
            return
        parts = self.args.split(None, 2)
        if len(parts) != 3 or not parts[2].lstrip("-+").isdigit():
            self.msg("Usage: setstat <target> <stat> <value>")
            return
        target_name, stat_key, value_str = parts
        target = self.caller.search(target_name, global_search=True)
        if not target:
            return
        value = int(value_str)
        alias_map = {"hp": "health", "mp": "mana", "sp": "stamina"}
        stat_key = alias_map.get(stat_key.lower(), stat_key)
        stat_key_up = stat_key.upper()
        stat_key_low = stat_key.lower()

        trait = target.traits.get(stat_key_up) or target.traits.get(stat_key_low)
        if trait:
            trait.base = value
            if stat_key_up in CORE_STAT_KEYS:
                base = target.db.base_primary_stats or {}
                base[stat_key_up] = value
                target.db.base_primary_stats = base
            else:
                overrides = target.db.stat_overrides or {}
                overrides[trait.key.lower()] = value
                target.db.stat_overrides = overrides
            stat_manager.refresh_stats(target)
            self.msg(f"{trait.key} set to {value} on {target.key}.")
            self.msg(get_display_scroll(target))
            return

        if stat_key_low in {"copper", "silver", "gold", "platinum"}:
            coins = target.db.coins or {}
            coins[stat_key_low] = value
            target.db.coins = coins
            stat_manager.refresh_stats(target)
            self.msg(f"{stat_key_low} set to {value} on {target.key}.")
            self.msg(get_display_scroll(target))
            return

        if stat_key_low == "sated":
            target.db.sated = value
            stat_manager.refresh_stats(target)
            self.msg(f"sated set to {value} on {target.key}.")
            self.msg(get_display_scroll(target))
            return

        if stat_key_low == "level":
            value = min(value, MAX_LEVEL)
            target.db.level = value
            stat_manager.refresh_stats(target)
            self.msg(f"level set to {value} on {target.key}.")
            self.msg(get_display_scroll(target))
            return

        if stat_key_low == "exp":
            target.db.exp = value
            stat_manager.refresh_stats(target)
            self.msg(f"exp set to {value} on {target.key}.")
            self.msg(get_display_scroll(target))
            return

        target.attributes.add(stat_key_low, value)
        stat_manager.refresh_stats(target)
        self.msg(f"{stat_key_low} set to {value} on {target.key}.")
        self.msg(get_display_scroll(target))


class CmdSetAttr(Command):
    """
    Set an arbitrary attribute on an object or character.

    Usage:
        setattr <target> <attr> <value>

    See |whelp setattr|n for details.
    """

    key = "setattr"
    aliases = ("setattribute",)
    locks = "cmd:perm(Admin) or perm(Builder)"
    help_category = "Admin"

    def func(self):
        if not self.args:
            self.msg("Usage: setattr <target> <attr> <value>")
            return
        parts = self.args.split(None, 2)
        if len(parts) < 3:
            self.msg("Usage: setattr <target> <attr> <value>")
            return
        target_name, attr, value = parts
        target = self.caller.search(target_name, global_search=True)
        if not target:
            return
        target.attributes.add(attr, value)
        self.msg(f"{attr} set on {target.key}.")


class CmdSetBounty(Command):
    """
    Assign a bounty to a character.

    Usage:
        setbounty <target> <amount>

    See |whelp setbounty|n for details.
    """

    key = "setbounty"
    locks = "cmd:perm(Admin)"
    help_category = "Admin"

    def func(self):
        if not self.args:
            self.msg("Usage: setbounty <target> <amount>")
            return
        parts = self.args.split(None, 1)
        if len(parts) != 2 or not parts[1].isdigit():
            self.msg("Usage: setbounty <target> <amount>")
            return
        target_name, amt_str = parts
        target = self.caller.search(target_name, global_search=True)
        if not target:
            return
        target.db.bounty = int(amt_str)
        self.msg(f"Bounty for {target.key} set to {amt_str}.")


class CmdSlay(Command):
    """
    Instantly reduce a target's health to zero.

    Usage:
        slay <target>

    See |whelp slay|n for details.
    """

    key = "slay"
    locks = "cmd:perm(Admin)"
    help_category = "Admin"

    def func(self):
        if not self.args:
            self.msg("Usage: slay <target>")
            return
        target = self.caller.search(self.args.strip(), global_search=True)
        if not target:
            return
        if not target.traits.get("health"):
            self.msg("Target has no health stat.")
            return
        target.traits.health.current = 0
        target.at_damage(self.caller, 0)
        self.msg(f"You slay {target.key}.")


class CmdSmite(Command):
    """
    Reduce a target to a single hit point.

    Usage:
        smite <target>

    See |whelp smite|n for details.
    """

    key = "smite"
    locks = "cmd:perm(Admin)"
    help_category = "Admin"

    def func(self):
        if not self.args:
            self.msg("Usage: smite <target>")
            return
        target = self.caller.search(self.args.strip(), global_search=True)
        if not target:
            return
        if not target.traits.get("health"):
            self.msg("Target has no health stat.")
            return
        target.traits.health.current = 1
        self.msg(f"You smite {target.key}, leaving them on the brink of death.")


class CmdRestoreAll(Command):
    """
    Fully heal every player and remove all buffs and status effects.

    Usage:
        restoreall

    See |whelp restoreall|n for details.
    """

    key = "restoreall"
    locks = "cmd:perm(Admin)"
    help_category = "Admin"

    def func(self):
        from typeclasses.characters import PlayerCharacter

        for pc in PlayerCharacter.objects.all():
            if pc.traits.get("health"):
                pc.traits.health.reset()
            if pc.traits.get("mana"):
                pc.traits.mana.reset()
            if pc.traits.get("stamina"):
                pc.traits.stamina.reset()
            pc.tags.clear(category="buff")
            pc.tags.clear(category="status")
            pc.db.status_effects = {}
            pc.db.temp_bonuses = {}
            pc.db.active_effects = {}
        self.msg("All player characters fully restored.")


class CmdPurge(Command):
    """
    Delete unwanted objects.

    Usage:
        purge
        purge <target>

    See |whelp purge|n for details.
    """

    key = "purge"
    locks = "cmd:perm(Admin)"
    help_category = "Admin"

    def func(self):
        caller = self.caller
        location = caller.location
        if not location:
            caller.msg("You have no location.")
            return

        if not self.args:
            removed = []
            for obj in list(location.contents):
                if obj is caller or obj.destination or obj.has_account:
                    continue
                if obj.location is None:
                    continue
                removed.append(obj.key)
                obj.delete()
            if removed:
                caller.msg("Purged: " + ", ".join(removed))
            else:
                caller.msg("Nothing to purge.")
            return

        target = caller.search(self.args.strip(), global_search=True)
        if not target:
            return
        if (
            target is caller
            or target.has_account
            or target.destination
            or target.location is None
        ):
            caller.msg("You cannot purge that.")
            return
        target.delete()
        caller.msg(f"Purged {target.key}.")


def _create_gear(
    caller,
    typeclass,
    name,
    slot=None,
    value=None,
    attr="dmg",
    desc=None,
    weight=0,
    identified=True,
):
    """Helper to create gear objects.

    Uses the given ``name`` as-is for the key and assigns a numbered
    alias based on how many objects with the same key already exist. A
    lowercase base alias matching ``name`` is always added.
    """

    from utils import format_ansi_title

    key = format_ansi_title(name)
    alias_base = strip_ansi(key).lower()
    count = ObjectDB.objects.filter(db_key__iexact=key).count()

    obj = create_object(typeclass, key=key, location=caller)
    if desc:
        obj.db.desc = desc
    obj.db.weight = weight
    obj.aliases.add(alias_base)
    obj.aliases.add(f"{alias_base}-{count + 1}")
    if slot:
        slot = normalize_slot(slot)
        if obj.is_typeclass("typeclasses.objects.ClothingObject", exact=False):
            obj.db.clothing_type = slot
        else:
            obj.db.slot = slot
        # mark the object as equipment and set identification state
        obj.tags.add("equipment", category="flag")
        if identified:
            obj.tags.add("identified", category="flag")
            obj.db.identified = True
        else:
            obj.tags.add("unidentified", category="flag")
            obj.db.identified = False
        for part in slot.split("/"):
            obj.tags.add(part, category="slot")
    if value is not None:
        obj.attributes.add(attr, value)
    caller.msg(f"Created {obj.get_display_name(caller)}.")
    return obj


class CmdCGear(Command):
    """
    Generic helper for gear creation.

    Usage:
        cgear [/unidentified] <typeclass> <name> [slot] [value] [weight]

    Only Builders may use this command.
    See |whelp cgear|n for details.
    """

    key = "cgear"
    locks = "cmd:perm(Builder) or perm(Admin) or perm(Developer)"
    help_category = "Building"

    def func(self):
        caller = self.caller
        if not caller.check_permstring("Builder"):
            caller.msg("You are not authorized to use this command.")
            return

        argstr = self.args.strip()
        identified = True
        for prefix in ("/unidentified", "/unid"):
            if argstr.lower().startswith(prefix):
                identified = False
                argstr = argstr[len(prefix) :].lstrip()
                break

        if not argstr:
            self.msg(
                "Usage: cgear [/unidentified] <typeclass> <name> [slot] [value] [weight] [stat_mods] <description>"
            )
            return
        try:
            parts = _safe_split(argstr)
        except ValueError as err:
            self.msg(str(err))
            return
        if len(parts) < 2:
            self.msg(
                "Usage: cgear [/unidentified] <typeclass> <name> [slot] [value] [weight] [stat_mods] <description>"
            )
            return
        tclass = parts[0]
        name = parts[1].strip("'\"")
        idx = 2
        slot = None
        if idx < len(parts) and not parts[idx].lstrip("-+").isdigit():
            slot = normalize_slot(parts[idx])
            idx += 1
        val = None
        if idx < len(parts):
            if parts[idx].lstrip("-+").isdigit():
                val = int(parts[idx])
                idx += 1
            else:
                self.msg("Value must be a number.")
                return
        weight = 0
        if idx < len(parts):
            if parts[idx].lstrip("-+").isdigit():
                weight = int(parts[idx])
                idx += 1
            else:
                self.msg("Weight must be a number.")
                return
        rest = " ".join(parts[idx:])
        try:
            bonuses, desc = parse_stat_mods(rest)
        except ValueError as err:
            self.msg(f"Invalid stat modifier: {err}. See 'help statmods' for valid stats.")
            return
        if slot and slot not in VALID_SLOTS:
            self.msg("Invalid slot name.")
            return

        obj = _create_gear(
            self.caller,
            tclass,
            name,
            slot,
            val,
            desc=desc,
            weight=weight,
            identified=identified,
        )
        if bonuses:
            obj.db.stat_mods = bonuses


class CmdOCreate(Command):
    """
    Create a generic object and put it in your inventory.

    Usage:
        ocreate <name>

    Only Builders may use this command.
    See |whelp ocreate|n for details.
    """

    key = "ocreate"
    locks = "cmd:perm(Builder) or perm(Admin) or perm(Developer)"
    help_category = "Building"

    def func(self):
        caller = self.caller
        if not caller.check_permstring("Builder"):
            caller.msg("You are not authorized to use this command.")
            return

        if not self.args:
            name = "object"
            weight = 0
        else:
            try:
                parts = _safe_split(self.args)
            except ValueError as err:
                self.msg(str(err))
                return
            if not parts:
                self.msg("Usage: ocreate <name>")
                return
            name = parts[0].strip("'\"")
            weight = 0
            weight_str = " ".join(parts[1:])
            if weight_str:
                if weight_str.isdigit():
                    weight = int(weight_str)
                else:
                    self.msg("Weight must be a number.")
                    return
        obj = _create_gear(
            self.caller,
            "typeclasses.objects.Object",
            name,
            desc=None,
            weight=weight,
        )
        self.msg(f"Created {obj.key}.")


class CmdCWeapon(Command):
    """
    Create a simple melee weapon.

    Usage:
        cweapon [/unidentified] <name> <slot> <damage> <weight> [stat_mods] <description>

    Only Builders may use this command.
    See |whelp cweapon|n for details.
    """

    key = "cweapon"
    locks = "cmd:perm(Builder) or perm(Admin) or perm(Developer)"
    help_category = "Building"

    def func(self):
        caller = self.caller
        if not caller.check_permstring("Builder"):
            caller.msg("You are not authorized to use this command.")
            return

        argstr = self.args.strip()
        identified = True
        for prefix in ("/unidentified", "/unid"):
            if argstr.lower().startswith(prefix):
                identified = False
                argstr = argstr[len(prefix) :].lstrip()
                break

        if not argstr:
            self.msg(
                "Usage: cweapon [/unidentified] <name> <slot> <damage> <weight> [stat_mods] <description>"
            )
            return

        try:
            parts = _safe_split(argstr)
        except ValueError as err:
            self.msg(str(err))
            return
        if len(parts) < 5:
            self.msg(
                "Usage: cweapon [/unidentified] <name> <slot> <damage> <weight> [stat_mods] <description>"
            )
            return
        name = parts[0].strip("'\"")
        slot = normalize_slot(parts[1])

        dmg_arg = parts[2]
        weight_str = parts[3]
        rest = " ".join(parts[4:])

        if slot not in VALID_SLOTS:
            self.msg("Invalid slot name.")
            return

        try:
            weight = int(weight_str)
        except ValueError:
            self.msg("Weight must be a number.")
            return

        bonuses = {}
        desc = None

        dmg = None
        dice = None
        dice_num = dice_sides = None
        if re.match(r"^\d+d\d+$", dmg_arg):
            dice = dmg_arg
            dice_num, dice_sides = map(int, dmg_arg.lower().split("d"))
        else:
            try:
                dmg = int(dmg_arg)
            except ValueError:
                self.msg("Damage must be a number or NdN dice string.")
                return

        if rest:
            pieces = [p.strip() for p in rest.split(",")]
            pattern = re.compile(r"([A-Za-z][A-Za-z _]*?)\+(-?\d+)")
            desc_parts = []
            for piece in pieces:
                if not piece:
                    continue
                match = pattern.match(piece)
                if match:
                    stat_name = match.group(1).strip()
                    amount = int(match.group(2))
                    key = normalize_stat_key(stat_name)
                    if key not in VALID_STATS:
                        self.msg(
                            f"Invalid stat modifier: {stat_name}. See 'help statmods' for valid stats."
                        )
                        return
                    bonuses[key] = amount
                    remainder = piece[match.end() :].strip()
                    if remainder:
                        desc_parts.append(remainder)
                        desc_parts.extend(
                            p.strip() for p in pieces[pieces.index(piece) + 1 :]
                        )
                        break
                else:
                    desc_parts.append(piece)
                    desc_parts.extend(
                        p.strip() for p in pieces[pieces.index(piece) + 1 :]
                    )
                    break
            if desc_parts:
                desc = ", ".join(desc_parts).strip()
        if desc is None and rest:
            desc = rest.strip()

        if slot not in VALID_SLOTS:
            self.msg("Invalid slot name.")
            return

        obj = _create_gear(
            self.caller,
            "typeclasses.gear.MeleeWeapon",
            name.capitalize(),
            slot,
            desc=desc,
            weight=weight,
            identified=identified,
        )

        if slot:
            if slot == "mainhand/offhand":
                obj.tags.add("mainhand", category="flag")
                obj.tags.add("offhand", category="flag")
            else:
                obj.tags.add(slot, category="flag")

        if dmg is not None:
            obj.attributes.add("dmg", dmg)
        if dice:
            obj.attributes.add("damage_dice", dice)
            obj.attributes.add("dice_num", dice_num)
            obj.attributes.add("dice_sides", dice_sides)
        if bonuses:
            obj.db.stat_mods = bonuses

        damage_display = dmg_arg
        self.caller.msg(
            f"Slot: {slot}\nDamage: {damage_display}\nWeight: {weight}\nDescription: {desc}"
        )


class CmdCShield(Command):
    """
    Create a shield piece of armor.

    Usage:
        cshield [/unidentified] <name> <armor_rating> <block_rate> <weight> [stat_mods] <description>

    Only Builders may use this command.
    See |whelp cshield|n for details.
    """

    key = "cshield"
    locks = "cmd:perm(Builder) or perm(Admin) or perm(Developer)"
    help_category = "Building"

    def func(self):
        caller = self.caller
        if not caller.check_permstring("Builder"):
            caller.msg("You are not authorized to use this command.")
            return

        argstr = self.args.strip()
        identified = True
        for prefix in ("/unidentified", "/unid"):
            if argstr.lower().startswith(prefix):
                identified = False
                argstr = argstr[len(prefix) :].lstrip()
                break

        if not argstr:
            self.msg(
                "Usage: cshield [/unidentified] <name> <armor_rating> <block_rate> <weight> [stat_mods] <description>"
            )
            return
        try:
            parts = _safe_split(argstr)
        except ValueError as err:
            self.msg(str(err))
            return
        if len(parts) < 5:
            self.msg(
                "Usage: cshield [/unidentified] <name> <armor_rating> <block_rate> <weight> [stat_mods] <description>"
            )
            return
        name = parts[0].strip("'\"")
        armor_str = parts[1]
        block_rate_str = parts[2]
        weight_str = parts[3]
        rest = " ".join(parts[4:])

        try:
            armor = int(armor_str)
        except ValueError:
            self.msg("Armor rating must be a number.")
            return

        try:
            block_rate = int(block_rate_str)
        except ValueError:
            self.msg("Block rate must be a number.")
            return

        try:
            weight = int(weight_str)
        except ValueError:
            self.msg("Weight must be a number.")
            return

        bonuses = {}
        desc = None
        if rest:
            pieces = [p.strip() for p in rest.split(",")]
            pattern = re.compile(r"([A-Za-z][A-Za-z _]*?)\+(-?\d+)")
            desc_parts = []
            for piece in pieces:
                if not piece:
                    continue
                match = pattern.match(piece)
                if match:
                    stat_name = match.group(1).strip()
                    amount = int(match.group(2))
                    key = normalize_stat_key(stat_name)
                    if key not in VALID_STATS:
                        self.msg(
                            f"Invalid stat modifier: {stat_name}. See 'help statmods' for valid stats."
                        )
                        return
                    bonuses[key] = amount
                    remainder = piece[match.end() :].strip()
                    if remainder:
                        desc_parts.append(remainder)
                        desc_parts.extend(
                            p.strip() for p in pieces[pieces.index(piece) + 1 :]
                        )
                        break
                else:
                    desc_parts.append(piece)
                    desc_parts.extend(
                        p.strip() for p in pieces[pieces.index(piece) + 1 :]
                    )
                    break
            if desc_parts:
                desc = ", ".join(desc_parts).strip()
        if desc is None and rest:
            desc = rest.strip()

        slot = normalize_slot("offhand")
        obj = _create_gear(
            self.caller,
            "typeclasses.objects.ClothingObject",
            name,
            slot,
            armor,
            attr="armor",
            desc=desc,
            weight=weight,
            identified=identified,
        )

        obj.tags.add("shield", category="flag")
        obj.db.block_rate = block_rate
        if bonuses:
            obj.db.modifiers = bonuses
            obj.db.stat_mods = bonuses

        msg = (
            f"Slot: {slot}\nArmor: {armor}\nBlock Rate: {block_rate}\nWeight: {weight}"
        )
        if bonuses:
            mods = ", ".join(f"{k}+{v}" for k, v in bonuses.items())
            msg += f"\nModifiers: {mods}"
        if desc:
            msg += f"\nDescription: {desc}"
        self.caller.msg(msg)


class CmdCArmor(Command):
    """
    Create a wearable armor item.

    Usage:
        carmor [/unidentified] <name> <slot> <weight> [stat_mods] <description>

    Only Builders may use this command.
    See |whelp carmor|n for details.
    """

    key = "carmor"
    locks = "cmd:perm(Builder) or perm(Admin) or perm(Developer)"
    help_category = "Building"

    def func(self):
        caller = self.caller
        if not caller.check_permstring("Builder"):
            caller.msg("You are not authorized to use this command.")
            return

        argstr = self.args.strip()
        identified = True
        for prefix in ("/unidentified", "/unid"):
            if argstr.lower().startswith(prefix):
                identified = False
                argstr = argstr[len(prefix) :].lstrip()
                break

        if not argstr:
            self.msg(
                "Usage: carmor [/unidentified] <name> <slot> <weight> [stat_mods] <description>"
            )
            return
        try:
            parts = _safe_split(argstr)
        except ValueError as err:
            self.msg(str(err))
            return
        if len(parts) < 3:
            self.msg(
                "Usage: carmor [/unidentified] <name> <slot> <weight> [stat_mods] <description>"
            )
            return
        name, slot, weight_str = parts[:3]
        name = name.strip("'\"")
        rest = " ".join(parts[3:])
        try:
            bonuses, desc = parse_stat_mods(rest)
        except ValueError as err:
            self.msg(f"Invalid stat modifier: {err}. See 'help statmods' for valid stats.")
            return
        slot = normalize_slot(slot)
        if slot not in VALID_SLOTS:
            self.msg("Invalid slot name.")
            return
        try:
            weight = int(weight_str)
        except ValueError:
            self.msg("Weight must be a number.")
            return
        obj = _create_gear(
            self.caller,
            "typeclasses.objects.ClothingObject",
            name,
            slot,
            desc=desc,
            weight=weight,
            identified=identified,
        )

        if bonuses:
            obj.db.stat_mods = bonuses

        self.caller.msg(
            f"Slot: {slot}\nWeight: {weight}\nDescription: {desc}"
        )


class CmdCTool(Command):
    """
    Create a crafting tool.

    Usage:
        ctool <name> [tag]

    Only Builders may use this command.
    See |whelp ctool|n for details.
    """

    key = "ctool"
    locks = "cmd:perm(Builder) or perm(Admin) or perm(Developer)"
    help_category = "Building"

    def func(self):
        caller = self.caller
        if not caller.check_permstring("Builder"):
            caller.msg("You are not authorized to use this command.")
            return

        if not self.args:
            self.msg("Usage: ctool <name> [tag] [weight] [stat_mods] <description>")
            return
        try:
            parts = _safe_split(self.args)
        except ValueError as err:
            self.msg(str(err))
            return
        if not parts:
            self.msg("Usage: ctool <name> [tag] [weight] [stat_mods] <description>")
            return
        name = parts[0].strip("'\"")
        tag = None
        weight = 0
        idx = 1
        if idx < len(parts):
            if parts[idx].isdigit():
                weight = int(parts[idx])
                idx += 1
            else:
                tag = parts[idx]
                idx += 1
                if idx < len(parts) and parts[idx].isdigit():
                    weight = int(parts[idx])
                    idx += 1
                elif idx < len(parts) and not parts[idx].isdigit():
                    self.msg("Weight must be a number.")
                    return
        rest = " ".join(parts[idx:])
        try:
            bonuses, desc = parse_stat_mods(rest)
        except ValueError as err:
            self.msg(f"Invalid stat modifier: {err}. See 'help statmods' for valid stats.")
            return
        obj = _create_gear(
            self.caller,
            "typeclasses.objects.Object",
            name,
            desc=desc,
            weight=weight,
        )
        if tag:
            obj.tags.add(tag, category="crafting_tool")
        if bonuses:
            obj.db.stat_mods = bonuses


class CmdCRing(Command):
    """
    Create a wearable ring.

    Usage:
        cring [/unidentified] <name> [slot] [weight]

    The slot defaults to ``ring1`` if omitted. You may specify ``ring2``
    instead to create a ring for the second slot.
    Only Builders may use this command.
    """

    key = "cring"
    locks = "cmd:perm(Builder) or perm(Admin) or perm(Developer)"
    help_category = "Building"

    def func(self):
        caller = self.caller
        if not caller.check_permstring("Builder"):
            caller.msg("You are not authorized to use this command.")
            return

        argstr = self.args.strip()
        identified = True
        for prefix in ("/unidentified", "/unid"):
            if argstr.lower().startswith(prefix):
                identified = False
                argstr = argstr[len(prefix) :].lstrip()
                break

        if not argstr:
            self.msg(
                "Usage: cring [/unidentified] <name> [slot] [weight] [stat_mods] <description>"
            )
            return
        try:
            parts = _safe_split(argstr)
        except ValueError as err:
            self.msg(str(err))
            return
        if not parts:
            self.msg(
                "Usage: cring [/unidentified] <name> [slot] [weight] [stat_mods] <description>"
            )
            return
        name = parts[0].strip("'\"")
        slot = "ring1"
        weight = 0
        idx = 1
        if idx < len(parts):
            if parts[idx].isdigit():
                weight = int(parts[idx])
                idx += 1
            else:
                slot = normalize_slot(parts[idx])
                idx += 1
                if idx < len(parts) and parts[idx].isdigit():
                    weight = int(parts[idx])
                    idx += 1
                elif idx < len(parts) and not parts[idx].isdigit():
                    self.msg("Weight must be a number.")
                    return
        rest = " ".join(parts[idx:])
        try:
            bonuses, desc = parse_stat_mods(rest)
        except ValueError as err:
            self.msg(f"Invalid stat modifier: {err}. See 'help statmods' for valid stats.")
            return

        if slot not in VALID_SLOTS:
            self.msg("Invalid slot name.")
            return

        obj = _create_gear(
            self.caller,
            "typeclasses.objects.ClothingObject",
            name,
            slot,
            desc=desc,
            weight=weight,
            identified=identified,
        )
        if bonuses:
            obj.db.stat_mods = bonuses


class CmdCTrinket(Command):
    """
    Create a wearable trinket.

    Usage:
        ctrinket [/unidentified] <name> [weight]

    Trinkets always use the ``trinket`` slot.
    Only Builders may use this command.
    """

    key = "ctrinket"
    locks = "cmd:perm(Builder) or perm(Admin) or perm(Developer)"
    help_category = "Building"

    def func(self):
        caller = self.caller
        if not caller.check_permstring("Builder"):
            caller.msg("You are not authorized to use this command.")
            return

        argstr = self.args.strip()
        identified = True
        for prefix in ("/unidentified", "/unid"):
            if argstr.lower().startswith(prefix):
                identified = False
                argstr = argstr[len(prefix) :].lstrip()
                break

        if not argstr:
            self.msg(
                "Usage: ctrinket [/unidentified] <name> [weight] [stat_mods] <description>"
            )
            return
        try:
            parts = _safe_split(argstr)
        except ValueError as err:
            self.msg(str(err))
            return
        if not parts:
            self.msg(
                "Usage: ctrinket [/unidentified] <name> [weight] [stat_mods] <description>"
            )
            return
        name = parts[0].strip("'\"")
        weight = 0
        idx = 1
        if idx < len(parts):
            if parts[idx].isdigit():
                weight = int(parts[idx])
                idx += 1
            else:
                self.msg("Weight must be a number.")
                return
        rest = " ".join(parts[idx:])
        try:
            bonuses, desc = parse_stat_mods(rest)
        except ValueError as err:
            self.msg(f"Invalid stat modifier: {err}. See 'help statmods' for valid stats.")
            return

        obj = _create_gear(
            self.caller,
            "typeclasses.objects.ClothingObject",
            name,
            normalize_slot("trinket"),
            desc=desc,
            weight=weight,
            identified=identified,
        )
        if bonuses:
            obj.db.stat_mods = bonuses


class CmdCFood(Command):
    """Create a food item.

    Only Builders may use this command.
    """

    key = "cfood"
    locks = "cmd:perm(Builder) or perm(Admin) or perm(Developer)"
    help_category = "Building"

    def func(self):
        caller = self.caller
        if not caller.check_permstring("Builder"):
            caller.msg("You are not authorized to use this command.")
            return

        try:
            parts = _safe_split(self.args)
        except ValueError as err:
            self.msg(str(err))
            return
        if len(parts) < 3:
            self.msg("Usage: cfood <name> <sated_boost> <description>")
            return
        name = parts[0].strip("'\"")
        boost_str = parts[1]
        rest = " ".join(parts[2:])
        if not boost_str.lstrip("-+").isdigit():
            self.msg("Sated boost must be a number.")
            return
        boost = int(boost_str)

        obj = _create_gear(
            self.caller,
            "typeclasses.objects.Object",
            name,
            desc=rest,
            weight=1,
        )
        obj.tags.add("edible")
        obj.db.item_type = "food"
        obj.db.type = "food"
        obj.db.sated = boost
        obj.db.sated_boost = boost
        obj.db.identified = True


class CmdCDrink(Command):
    """Create a drink item.

    Only Builders may use this command.
    """

    key = "cdrink"
    locks = "cmd:perm(Builder) or perm(Admin) or perm(Developer)"
    help_category = "Building"

    def func(self):
        caller = self.caller
        if not caller.check_permstring("Builder"):
            caller.msg("You are not authorized to use this command.")
            return

        try:
            parts = _safe_split(self.args)
        except ValueError as err:
            self.msg(str(err))
            return
        if len(parts) < 3:
            self.msg("Usage: cdrink <name> <sated_boost> <description>")
            return
        name = parts[0].strip("'\"")
        boost_str = parts[1]
        rest = " ".join(parts[2:])
        if not boost_str.lstrip("-+").isdigit():
            self.msg("Sated boost must be a number.")
            return
        boost = int(boost_str)

        obj = _create_gear(
            self.caller,
            "typeclasses.objects.Object",
            name,
            desc=rest,
            weight=1,
        )
        obj.tags.add("edible")
        obj.db.item_type = "drink"
        obj.db.type = "drink"
        obj.db.sated = boost
        obj.db.sated_boost = boost
        obj.db.identified = True


class CmdCPotion(Command):
    """Create a potion item.

    Only Builders may use this command.
    """

    key = "cpotion"
    locks = "cmd:perm(Builder) or perm(Admin) or perm(Developer)"
    help_category = "Building"

    def func(self):
        caller = self.caller
        if not caller.check_permstring("Builder"):
            caller.msg("You are not authorized to use this command.")
            return

        try:
            parts = _safe_split(self.args)
        except ValueError as err:
            self.msg(str(err))
            return
        if len(parts) < 2:
            self.msg("Usage: cpotion <name> <bonuses> <description>")
            return
        name = parts[0].strip("'\"")
        rest = " ".join(parts[1:])
        try:
            bonuses, desc = parse_stat_mods(rest)
        except ValueError as err:
            self.msg(f"Invalid stat modifier: {err}. See 'help statmods' for valid stats.")
            return

        obj = _create_gear(
            self.caller,
            "typeclasses.objects.Object",
            name,
            desc=desc,
            weight=1,
        )
        obj.tags.add("edible")
        obj.db.item_type = "drink"
        obj.db.type = "drink"
        obj.db.is_potion = True
        obj.db.identified = True
        if bonuses:
            obj.db.buffs = bonuses


class AdminCmdSet(CmdSet):
    """Command set with admin utilities."""

    key = "Admin CmdSet"

    def at_cmdset_creation(self):
        super().at_cmdset_creation()
        self.add(CmdSetStat)
        self.add(CmdSetAttr)
        self.add(CmdSetBounty)
        self.add(CmdSlay)
        self.add(CmdSmite)
        self.add(CmdRestoreAll)
        self.add(CmdPurge)
        self.add(CmdScan)


class BuilderCmdSet(CmdSet):
    """Command set with builder utilities."""

    key = "Builder CmdSet"

    def at_cmdset_creation(self):
        super().at_cmdset_creation()
        self.add(CmdSetStat)
        self.add(CmdSetAttr)
        self.add(CmdOCreate)
        self.add(CmdCWeapon)
        self.add(CmdCShield)
        self.add(CmdCArmor)
        self.add(CmdCTool)
        self.add(CmdCFood)
        self.add(CmdCDrink)
        self.add(CmdCPotion)
        self.add(CmdCRing)
        self.add(CmdCTrinket)
        self.add(CmdCGear)
        self.add(CmdSetDesc)
        self.add(CmdSetWeight)
        self.add(CmdSetSlot)
        self.add(CmdSetDamage)
        self.add(CmdSetBuff)
        self.add(CmdSetFlag)
        self.add(CmdRemoveFlag)
        self.add(CmdCNPC)
