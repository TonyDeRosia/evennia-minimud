from evennia import CmdSet, create_object
from evennia.objects.models import ObjectDB
import re
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
from world.stats import CORE_STAT_KEYS
from world.system import stat_manager
from utils.stats_utils import get_display_scroll


class CmdSetStat(Command):
    """
    Set a base or derived stat on a target.

    Usage:
        setstat <target> <stat> <value>
    """

    key = "setstat"
    aliases = ("set",)
    locks = "cmd:perm(Admin) or perm(Builder)"
    help_category = "admin"

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
    Set an arbitrary attribute on a target.

    Usage:
        setattr <target> <attr> <value>
    """

    key = "setattr"
    aliases = ("setattribute",)
    locks = "cmd:perm(Admin) or perm(Builder)"
    help_category = "admin"

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
    Set the bounty value on a target.

    Usage:
        setbounty <target> <amount>
    """

    key = "setbounty"
    locks = "cmd:perm(Admin)"
    help_category = "admin"

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
    Instantly defeat a target.

    Usage:
        slay <target>
    """

    key = "slay"
    locks = "cmd:perm(Admin)"
    help_category = "admin"

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
    """

    key = "smite"
    locks = "cmd:perm(Admin)"
    help_category = "admin"

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
    """Fully restore all player characters."""

    key = "restoreall"
    locks = "cmd:perm(Admin)"
    help_category = "admin"

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
    """Remove unwanted objects.

    Usage:
        purge
        purge <target>

    Without arguments this deletes all objects in the caller's
    current room except for the caller themselves. With an argument
    it deletes the specified target. Players, exits and rooms are
    protected from deletion.
    """

    key = "purge"
    locks = "cmd:perm(Admin)"
    help_category = "admin"

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
        if target is caller or target.has_account or target.destination or target.location is None:
            caller.msg("You cannot purge that.")
            return
        target.delete()
        caller.msg(f"Purged {target.key}.")


def _create_gear(
    caller, typeclass, name, slot=None, value=None, attr="dmg", desc=None, weight=0
):
    """Helper to create gear objects.

    Uses the given ``name`` as-is for the key and assigns a numbered
    alias based on how many objects with the same key already exist. A
    lowercase base alias matching ``name`` is always added.
    """

    key = name
    alias_base = key.lower()
    count = ObjectDB.objects.filter(db_key__iexact=key).count()

    obj = create_object(typeclass, key=key, location=caller)
    if desc:
        obj.db.desc = desc
    obj.db.weight = weight
    obj.aliases.add(alias_base)
    obj.aliases.add(f"{alias_base}-{count + 1}")
    if slot:
        if obj.is_typeclass("typeclasses.objects.ClothingObject", exact=False):
            obj.db.clothing_type = slot
        else:
            obj.db.slot = slot
        # mark the object as equipment and identified
        obj.tags.add("equipment", category="flag")
        obj.tags.add("identified", category="flag")
        obj.db.identified = True
        for part in slot.split("/"):
            obj.tags.add(part, category="slot")
    if value is not None:
        obj.attributes.add(attr, value)
    caller.msg(f"Created {obj.get_display_name(caller)}.")
    return obj


class CmdCGear(Command):
    """Create a generic gear item."""

    key = "cgear"
    locks = "cmd:perm(Builder)"
    help_category = "Building"

    def func(self):
        if not self.args:
            self.msg("Usage: cgear <typeclass> <name> [slot] [value] [weight]")
            return
        parts = self.args.split()
        if len(parts) < 2:
            self.msg("Usage: cgear <typeclass> <name> [slot] [value] [weight]")
            return
        tclass = parts[0]
        name = parts[1]
        slot = parts[2] if len(parts) > 2 else None
        val = None
        weight = 0
        if len(parts) > 3:
            try:
                val = int(parts[3])
            except ValueError:
                self.msg("Value must be a number.")
                return
        if len(parts) > 4:
            try:
                weight = int(parts[4])
            except ValueError:
                self.msg("Weight must be a number.")
                return
        _create_gear(self.caller, tclass, name, slot, val, desc=None, weight=weight)


class CmdOCreate(Command):
    """Create a generic object."""

    key = "ocreate"
    locks = "cmd:perm(Builder)"
    help_category = "Building"

    def func(self):
        if not self.args:
            name = "object"
            weight = 0
        else:
            parts = self.args.split(None, 1)
            name = parts[0]
            weight = 0
            if len(parts) > 1:
                if parts[1].isdigit():
                    weight = int(parts[1])
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
    """Create a simple weapon."""

    key = "cweapon"
    locks = "cmd:perm(Builder)"
    help_category = "Building"

    def func(self):
        if not self.args:
            self.msg("Usage: cweapon <name> <slot> <damage> [weight] [description]")
            return
        parts = self.args.split(None, 4)
        if len(parts) < 3:
            self.msg("Usage: cweapon <name> <slot> <damage> [weight] [description]")
            return
        name = parts[0]
        slot = parts[1].lower()
        weight = 0
        desc = None
        remaining = parts[3:] if len(parts) > 3 else []

        dmg = None
        dice = None
        dice_num = dice_sides = None
        if len(parts) > 2:
            dmg_arg = parts[2]
            if re.match(r"^\d+d\d+$", dmg_arg):
                dice = dmg_arg
                dice_num, dice_sides = map(int, dmg_arg.lower().split("d"))
            else:
                try:
                    dmg = int(dmg_arg)
                except ValueError:
                    self.msg("Damage must be a number or NdN dice string.")
                    return

        if remaining:
            if remaining[0].isdigit():
                weight = int(remaining[0])
                if len(remaining) > 1:
                    desc = " ".join(remaining[1:])
            else:
                desc = " ".join(remaining)

        valid_slots = {"mainhand", "offhand", "mainhand/offhand", "twohanded"}
        if slot and slot not in valid_slots:
            self.msg("Slot must be mainhand, offhand, mainhand/offhand, or twohanded.")
            return

        obj = _create_gear(
            self.caller,
            "typeclasses.gear.MeleeWeapon",
            name.capitalize(),
            slot,
            desc=desc,
            weight=weight,
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


class CmdCShield(Command):
    """Create a shield."""

    key = "cshield"
    locks = "cmd:perm(Builder)"
    help_category = "Building"

    def func(self):
        if not self.args:
            self.msg("Usage: cshield <name> [slot] [armor] [weight]")
            return
        parts = self.args.split()
        name = parts[0]
        slot = parts[1] if len(parts) > 1 else None
        armor = None
        weight = 0
        if len(parts) > 2:
            try:
                armor = int(parts[2])
            except ValueError:
                self.msg("Armor must be a number.")
                return
        if len(parts) > 3:
            try:
                weight = int(parts[3])
            except ValueError:
                self.msg("Weight must be a number.")
                return
        _create_gear(
            self.caller,
            "typeclasses.objects.ClothingObject",
            name,
            slot,
            armor,
            attr="armor",
            desc=None,
            weight=weight,
        )


class CmdCArmor(Command):
    """Create an armor piece."""

    key = "carmor"
    locks = "cmd:perm(Builder)"
    help_category = "Building"

    def func(self):
        if not self.args:
            self.msg("Usage: carmor <name> [slot] [armor] [weight]")
            return
        parts = self.args.split()
        name = parts[0]
        slot = parts[1] if len(parts) > 1 else None
        armor = None
        weight = 0
        if len(parts) > 2:
            try:
                armor = int(parts[2])
            except ValueError:
                self.msg("Armor must be a number.")
                return
        if len(parts) > 3:
            try:
                weight = int(parts[3])
            except ValueError:
                self.msg("Weight must be a number.")
                return
        _create_gear(
            self.caller,
            "typeclasses.objects.ClothingObject",
            name,
            slot,
            armor,
            attr="armor",
            desc=None,
            weight=weight,
        )


class CmdCTool(Command):
    """Create a crafting tool."""

    key = "ctool"
    locks = "cmd:perm(Builder)"
    help_category = "Building"

    def func(self):
        if not self.args:
            self.msg("Usage: ctool <name> [tag] [weight]")
            return
        parts = self.args.split()
        name = parts[0]
        tag = None
        weight = 0
        if len(parts) > 1:
            if parts[1].isdigit():
                weight = int(parts[1])
            else:
                tag = parts[1]
                if len(parts) > 2:
                    if parts[2].isdigit():
                        weight = int(parts[2])
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
        if tag:
            obj.tags.add(tag, category="crafting_tool")


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
        self.add(CmdCGear)
        self.add(CmdSetDesc)
        self.add(CmdSetWeight)
        self.add(CmdSetSlot)
        self.add(CmdSetDamage)
        self.add(CmdSetBuff)
        self.add(CmdSetFlag)
        self.add(CmdRemoveFlag)

