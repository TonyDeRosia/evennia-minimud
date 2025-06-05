from evennia import CmdSet
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
    aliases = ("statset",)
    locks = "cmd:perm(Admin)"
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
        trait = target.traits.get(stat_key_low)
        if trait:
            trait.base = value
        else:
            target.traits.add(stat_key_low, stat_key_low, base=value)
        data = target.db.derived_stats or {}
        data[stat_key_low] = value
        target.db.derived_stats = data
        self.msg(f"{stat_key_low} set to {value} on {target.key}.")


class CmdSetAttr(Command):
    """
    Set an arbitrary attribute on a target.

    Usage:
        setattr <target> <attr> <value>
    """

    key = "setattr"
    aliases = ("setattribute",)
    locks = "cmd:perm(Admin)"
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
        self.add(CmdScan)

