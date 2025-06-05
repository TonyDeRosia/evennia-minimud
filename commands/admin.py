from evennia import CmdSet, create_object
from .command import Command
from .info import CmdScan
from world.stats import CORE_STAT_KEYS
from world.system import stat_manager


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
        if stat_key_up in CORE_STAT_KEYS:
            trait = target.traits.get(stat_key_up)
            if trait:
                trait.base = value
            else:
                target.traits.add(stat_key_up, stat_key_up, base=value)
            base = target.db.base_primary_stats or {}
            base[stat_key_up] = value
            target.db.base_primary_stats = base
            stat_manager.refresh_stats(target)
            self.msg(f"{stat_key_up} set to {value} on {target.key}.")
            return
        stat_key_low = stat_key.lower()
        overrides = target.db.stat_overrides or {}
        overrides[stat_key_low] = value
        target.db.stat_overrides = overrides
        stat_manager.refresh_stats(target)
        self.msg(f"{stat_key_low} set to {value} on {target.key}.")


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


def _create_gear(caller, typeclass, name, slot=None, value=None, attr="dmg"):
    """Helper to create gear objects."""
    obj = create_object(typeclass, key=name, location=caller)
    if slot:
        if obj.is_typeclass("typeclasses.objects.ClothingObject", exact=False):
            obj.db.clothing_type = slot
        else:
            obj.db.slot = slot
    if value is not None:
        obj.db[attr] = value
    caller.msg(f"Created {obj.get_display_name(caller)}.")
    return obj


class CmdCGear(Command):
    """Create a generic gear item."""

    key = "cgear"
    locks = "cmd:perm(Builder)"
    help_category = "Building"

    def func(self):
        if not self.args:
            self.msg("Usage: cgear <typeclass> <name> [slot] [value]")
            return
        parts = self.args.split()
        if len(parts) < 2:
            self.msg("Usage: cgear <typeclass> <name> [slot] [value]")
            return
        tclass = parts[0]
        name = parts[1]
        slot = parts[2] if len(parts) > 2 else None
        val = None
        if len(parts) > 3:
            try:
                val = int(parts[3])
            except ValueError:
                self.msg("Value must be a number.")
                return
        _create_gear(self.caller, tclass, name, slot, val)


class CmdOCreate(Command):
    """Create a generic object."""

    key = "ocreate"
    locks = "cmd:perm(Builder)"
    help_category = "Building"

    def func(self):
        name = self.args.strip() or "object"
        create_object("typeclasses.objects.Object", key=name, location=self.caller)
        self.msg(f"Created {name}.")


class CmdCWeapon(Command):
    """Create a simple weapon."""

    key = "cweapon"
    locks = "cmd:perm(Builder)"
    help_category = "Building"

    def func(self):
        if not self.args:
            self.msg("Usage: cweapon <name> [slot] [damage]")
            return
        parts = self.args.split()
        name = parts[0]
        slot = parts[1] if len(parts) > 1 else None
        dmg = None
        if len(parts) > 2:
            try:
                dmg = int(parts[2])
            except ValueError:
                self.msg("Damage must be a number.")
                return
        _create_gear(self.caller, "typeclasses.gear.MeleeWeapon", name, slot, dmg)


class CmdCShield(Command):
    """Create a shield."""

    key = "cshield"
    locks = "cmd:perm(Builder)"
    help_category = "Building"

    def func(self):
        if not self.args:
            self.msg("Usage: cshield <name> [slot] [armor]")
            return
        parts = self.args.split()
        name = parts[0]
        slot = parts[1] if len(parts) > 1 else None
        armor = None
        if len(parts) > 2:
            try:
                armor = int(parts[2])
            except ValueError:
                self.msg("Armor must be a number.")
                return
        _create_gear(self.caller, "typeclasses.objects.ClothingObject", name, slot, armor, attr="armor")


class CmdCArmor(Command):
    """Create an armor piece."""

    key = "carmor"
    locks = "cmd:perm(Builder)"
    help_category = "Building"

    def func(self):
        if not self.args:
            self.msg("Usage: carmor <name> [slot] [armor]")
            return
        parts = self.args.split()
        name = parts[0]
        slot = parts[1] if len(parts) > 1 else None
        armor = None
        if len(parts) > 2:
            try:
                armor = int(parts[2])
            except ValueError:
                self.msg("Armor must be a number.")
                return
        _create_gear(self.caller, "typeclasses.objects.ClothingObject", name, slot, armor, attr="armor")


class CmdCTool(Command):
    """Create a crafting tool."""

    key = "ctool"
    locks = "cmd:perm(Builder)"
    help_category = "Building"

    def func(self):
        if not self.args:
            self.msg("Usage: ctool <name> [tag]")
            return
        parts = self.args.split()
        name = parts[0]
        tag = parts[1] if len(parts) > 1 else None
        obj = _create_gear(self.caller, "typeclasses.objects.Object", name)
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

