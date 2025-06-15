from evennia import CmdSet
from evennia.commands.default.general import CmdLook as DefaultCmdLook

from .command import Command


class CmdRest(Command):
    """
    Sit down to recover stamina. Usage: rest

    Usage:
        rest

    See |whelp rest|n for details.
    """

    key = "rest"
    aliases = ("relax",)
    help_category = "General"

    def func(self):
        caller = self.caller
        if caller.tags.has("sitting", category="status"):
            caller.msg("You are already resting.")
            return
        caller.tags.remove("sleeping", category="status")
        caller.tags.remove("lying down", category="status")
        caller.tags.add("sitting", category="status")
        caller.at_emote("$conj(sits) down to rest.")


class CmdSleep(Command):
    """
    Lie down and go to sleep. Usage: sleep

    Usage:
        sleep

    See |whelp sleep|n for details.
    """

    key = "sleep"
    help_category = "General"

    def func(self):
        caller = self.caller
        if caller.tags.has("sleeping", category="status"):
            caller.msg("You are already sleeping.")
            return
        caller.tags.remove("sitting", category="status")
        caller.tags.add("lying down", category="status")
        caller.tags.add("sleeping", category="status")
        caller.at_emote("$conj(closes) $pron(your) eyes and drifts to sleep.")


class CmdWake(Command):
    """
    Stand up from rest or sleep. Usage: wake

    Usage:
        wake

    See |whelp wake|n for details.
    """

    key = "wake"
    aliases = ("stand",)
    help_category = "General"

    def func(self):
        caller = self.caller
        if not any(
            caller.tags.has(tag, category="status")
            for tag in ("sleeping", "lying down", "sitting")
        ):
            caller.msg("You are already standing.")
            return
        caller.tags.remove("sleeping", category="status")
        caller.tags.remove("lying down", category="status")
        caller.tags.remove("sitting", category="status")
        caller.at_emote("$conj(stands) up.")


class CmdLook(DefaultCmdLook):
    """
    Look around the area unless you are sleeping.

    The `look` command shows your current room's description and clearly lists:

    1. Environmental objects (e.g., altars, pools)
    2. Non-player characters (e.g., guards, merchants)
    3. Visible items and loot
    4. Other players in the room

    Usage:
        look [<target>]

    Example:
        look

    Note:
        If there are no rooms nearby, this command will not work.
    """

    aliases = ("l", "look in", "l in")

    def parse(self):
        super().parse()
        if self.args and self.args.lower().startswith("in "):
            self.args = self.args[3:].strip()

    def func(self):
        if self.caller.tags.has("sleeping", category="status"):
            self.caller.msg("You can't see anything with your eyes closed.")
            return
        super().func()


class RestCmdSet(CmdSet):
    key = "Rest CmdSet"

    def at_cmdset_creation(self):
        super().at_cmdset_creation()
        self.add(CmdRest)
        self.add(CmdSleep)
        self.add(CmdWake)
        self.add(CmdLook)
