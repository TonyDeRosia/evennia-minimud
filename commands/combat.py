from random import choice
from evennia import CmdSet
from evennia.utils import iter_to_str
from evennia.utils.evtable import EvTable

from .command import Command
from typeclasses.gear import BareHand
from typeclasses.scripts import get_or_create_combat_script


class CmdAttack(Command):
    """
    Attack an enemy. Usage: attack <target> [with <weapon>]

    Usage:
        attack

    See |whelp attack|n for details.
    """

    key = "attack"
    aliases = ("att", "hit", "shoot")
    help_category = "Combat"

    def parse(self):
        """
        Parse for optional weapon
        """
        self.args = self.args.strip()

        # split on variations of "with"
        if " with " in self.args:
            self.target, self.weapon = self.args.split(" with ", maxsplit=1)
        elif " w " in self.args:
            self.target, self.weapon = self.args.split(" w ", maxsplit=1)
        elif " w/" in self.args:
            self.target, self.weapon = self.args.split(" w/", maxsplit=1)
        else:
            # no splitters, it's all target
            self.target = self.args
            self.weapon = None

    def func(self):
        location = self.caller.location
        if not location:
            self.msg("You cannot fight nothingness.")
            return

        if not self.target:
            self.msg("Attack what?")
            return

        # if we specified a weapon, find it first
        if self.weapon:
            weapon = self.caller.search(self.weapon)
            if not weapon:
                # no valid match
                return
        else:
            # grab whatever we're wielding
            if wielded := self.caller.wielding:
                weapon = wielded[0]
            else:
                # use our bare hands if we aren't wielding anything
                weapon = BareHand()

        # find our enemy!
        target = self.caller.search(self.target)
        if not target:
            # no valid match
            return
        if not target.db.can_attack:
            # this isn't something you can attack
            self.msg(f"You can't attack {target.get_display_name(self.caller)}.")
            return

        # if we were trying to flee, cancel that
        del self.caller.db.fleeing

        # it's all good! let's get started!
        combat_script = get_or_create_combat_script(location)
        current_fighters = combat_script.fighters

        # adding a combatant to combat just returns True if they're already there, so this is safe
        if not combat_script.add_combatant(self.caller, enemy=target):
            self.msg("You can't fight right now.")
            return

        self.caller.db.combat_target = target
        # execute the actual attack
        self.caller.attack(target, weapon)

        # check if we have auto-attack in settings
        if self.account and (settings := self.account.db.settings):
            if settings.get("auto attack"):
                # let the player know we'll be auto-attacking
                self.msg(f"[ Auto-attack is ON ]")

    def at_post_cmd(self):
        """
        optional post-command auto prompt
        """
        # check if we have auto-prompt in settings
        if self.account and (settings := self.account.db.settings):
            if settings.get("auto prompt"):
                status = self.caller.get_display_status(self.caller)
                self.msg(prompt=status)


class CmdWield(Command):
    """
    Wield a weapon. Usage: wield <weapon> [in <hand>]

    Usage:
        wield

    See |whelp wield|n for details.
    """

    key = "wield"
    aliases = ("hold",)
    help_category = "Combat"

    def parse(self):
        """
        Parse for optional weapon
        """
        self.args = self.args.strip()

        # split on the word "in"
        if " in " in self.args:
            self.weapon, self.hand = self.args.split(" in ", maxsplit=1)
        else:
            # no splitter, it's all target
            self.weapon = self.args
            self.hand = None

    def func(self):
        caller = self.caller

        # check if we have free hands
        if not (hands := caller.free_hands):
            self.msg(
                f"You have no free hands! You are already wielding {iter_to_str(caller.wielding)}."
            )
            return

        # filter for hands matching the optional hand input
        if self.hand:
            hands = [hand for hand in caller.free_hands if self.hand in hand]
            if not hands:
                self.msg(f"You do not have a free {self.hand}.")
                return

            # grab the top hand option
            hand = hands[0]
        else:
            hand = None

        weapon = caller.search(self.weapon, location=caller)
        if not weapon:
            # no valid object found
            return

        # try to wield the weapon
        held_in = caller.at_wield(weapon, hand=hand)
        if held_in:
            hand = "hand" if len(held_in) == 1 else "hands"
            # success!
            self.caller.at_emote(
                f"$conj(wields) the {{weapon}} in $pron(your) {iter_to_str(held_in)} {hand}.",
                mapping={"weapon": weapon},
            )


class CmdUnwield(Command):
    """
    Stop wielding a weapon. Usage: unwield <weapon>

    Usage:
        unwield

    See |whelp unwield|n for details.
    """

    key = "unwield"
    aliases = ("unhold",)
    help_category = "Combat"

    def func(self):
        caller = self.caller

        weapon = caller.search(self.args, candidates=caller.wielding)
        if not weapon:
            # no valid object found
            return

        freed_hands = caller.at_unwield(weapon)
        if freed_hands:
            # success!
            hand = "hand" if len(freed_hands) == 1 else "hands"
            self.caller.at_emote(
                f"$conj(releases) the {{weapon}} from $pron(your) {iter_to_str(freed_hands)} {hand}.",
                mapping={"weapon": weapon},
            )


class CmdFlee(Command):
    """
    Attempt to escape from combat. Usage: flee

    Usage:
        flee

    See |whelp flee|n for details.
    """

    key = "flee"
    help_category = "Combat"

    def func(self):
        caller = self.caller

        if not caller.in_combat:
            self.msg("You are not in combat.")
            return

        if not caller.can_flee:
            # this does its own error messaging
            return

        exits = caller.location.contents_get(content_type="exit")
        if not exits:
            self.msg("There is nowhere to flee to!")
            return

        if combat_script := caller.location.scripts.get("combat"):
            combat_script = combat_script[0]
            if not combat_script.remove_combatant(self.caller):
                self.msg("You cannot leave combat.")

        self.caller.db.fleeing = True
        self.msg("You flee!")
        flee_dir = choice(exits)
        self.execute_cmd(flee_dir.name)

class CmdBerserk(Command):
    """Enter a furious rage, increasing your strength temporarily."""

    key = "berserk"
    help_category = "Combat"

    def func(self):
        caller = self.caller
        from world.system import state_manager

        if state_manager.has_effect(caller, "berserk"):
            self.msg("You are already consumed by rage!")
            return

        stamina = caller.traits.get("stamina")
        if stamina and stamina.current < 10:
            self.msg("You are far too tired to work yourself into a rage.")
            return

        if stamina:
            stamina.current -= 10

        state_manager.add_effect(caller, "berserk", 5)
        caller.location.msg_contents(
            f"{caller.get_display_name(caller)} flies into a berserk rage!"
        )

    def at_post_cmd(self):
        """
        optional post-command auto prompt
        """
        # check if we have auto-prompt in settings
        if self.account and (settings := self.account.db.settings):
            if settings.get("auto prompt"):
                status = self.caller.get_display_status(self.caller)
                self.msg(prompt=status)


class CmdRespawn(Command):
    """
    Return to town after being defeated. Usage: respawn

    Usage:
        respawn

    See |whelp respawn|n for details.
    """

    key = "respawn"
    help_category = "Combat"

    def func(self):
        caller = self.caller

        if not caller.tags.has("unconscious", category="status"):
            self.msg("You are not defeated.")
            return
        caller.respawn()


class CmdRevive(Command):
    """
    Revive a defeated player at partial health.

    Usage:
        revive <player>
        revive all

    See |whelp revive|n for details.
    """

    key = "revive"
    aliases = ("resurrect",)
    help_category = "Combat"

    def func(self):
        caller = self.caller

        if not self.args:
            self.msg("Revive who?")
            return

        arg = self.args.strip()

        if arg.lower() == "all":
            from evennia.utils.search import search_tag

            targets = [
                obj
                for obj in search_tag(key="unconscious", category="status")
                if hasattr(obj, "revive")
            ]
            if not targets:
                self.msg("No one is unconscious.")
                return
            for target in targets:
                target.revive(caller)
            return

        target = caller.search(arg)
        if not target:
            return

        if not target.tags.has("unconscious", category="status"):
            self.msg(f"{target.get_display_name(caller)} is not defeated.")
            return

        target.revive(caller)


class CmdStatus(Command):
    key = "status"
    aliases = ("hp", "stat")

    def func(self):
        if not self.args:
            target = self.caller
            status = target.get_display_status(self.caller)
            self.msg(prompt=status)
        else:
            target = self.caller.search(self.args.strip())
            if not target:
                # no valid object found
                return
            status = target.get_display_status(self.caller)
            self.msg(status)


class CombatCmdSet(CmdSet):
    key = "Combat CmdSet"

    def at_cmdset_creation(self):
        super().at_cmdset_creation()

        self.add(CmdAttack)
        self.add(CmdFlee)
        self.add(CmdBerserk)
        self.add(CmdWield)
        self.add(CmdUnwield)
        self.add(CmdRevive)
        self.add(CmdRespawn)
        self.add(CmdStatus)
