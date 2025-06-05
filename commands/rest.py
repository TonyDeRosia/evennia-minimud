from evennia import CmdSet
from evennia.commands.default.general import CmdLook as DefaultCmdLook

from .command import Command


class CmdRest(Command):
    """Sit down and rest."""

    key = "rest"
    aliases = ("relax",)
    help_category = "general"

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
    """Lie down and go to sleep."""

    key = "sleep"
    help_category = "general"

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
    """Stand up and wake from rest or sleep."""

    key = "wake"
    aliases = ("stand",)
    help_category = "general"

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
    """Look around, unless you are sleeping."""

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
