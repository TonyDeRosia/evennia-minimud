"""
Command sets

All commands in the game must be grouped in a cmdset.  A given command
can be part of any number of cmdsets and cmdsets can be added/removed
and merged onto entities at runtime.

To create new commands to populate the cmdset, see
`commands/command.py`.

This module wraps the default command sets of Evennia; overloads them
to add/remove commands from the default lineup. You can create your
own cmdsets by inheriting from them or directly from `evennia.CmdSet`.

"""

from evennia import default_cmds
from evennia.contrib.game_systems.clothing import ClothedCharacterCmdSet
from commands.equip import CmdWear
from commands.help import CmdHelp

from evennia.contrib.game_systems.containers.containers import ContainerCmdSet
from evennia.contrib.grid.xyzgrid.commands import XYZGridCmdSet
from commands.movement import MovementCmdSet
from evennia.contrib.rpg.character_creator.character_creator import ContribCmdCharCreate
from evennia.contrib.game_systems.crafting.crafting import CmdCraft


from commands.combat import CombatCmdSet
from commands.skills import SkillCmdSet
from commands.interact import InteractCmdSet
from commands.equipment import EquipmentCmdSet
from commands.account import AccountOptsCmdSet
from commands.shops import CmdMoney
from commands.bank import CmdBank
from commands.info import InfoCmdSet
from commands.guilds import GuildCmdSet
from commands.rest import RestCmdSet
from commands.loot import LootCmdSet
from commands.who import CmdWho
from commands.recall import RecallCmdSet
from commands.building import CmdDig, CmdTeleport, CmdDelRoom, CmdRDel, CmdLink
from commands.areas import AreaCmdSet
from commands.room_flags import RoomFlagCmdSet
from commands.admin import AdminCmdSet, BuilderCmdSet
from commands.quests import QuestCmdSet
from commands.achievements import AchievementCmdSet
from commands.spells import SpellCmdSet
from commands.abilities import AbilityCmdSet


class CharacterCmdSet(default_cmds.CharacterCmdSet):
    """
    The `CharacterCmdSet` contains general in-game commands like `look`,
    `get`, etc available on in-game Character objects. It is merged with
    the `AccountCmdSet` when an Account puppets a Character.
    """

    key = "DefaultCharacter"

    def at_cmdset_creation(self):
        """
        Populates the cmdset
        """
        super().at_cmdset_creation()
        #
        # any commands you add below will overload the default ones.
        #
        self.add(CmdHelp())
        self.add(ClothedCharacterCmdSet)
        self.add(CmdWear())
        self.add(CmdMoney)
        self.add(CmdBank)
        self.add(ContainerCmdSet)
        self.add(MovementCmdSet)
        self.add(XYZGridCmdSet)
        self.add(CmdCraft)
        self.add(CombatCmdSet)
        self.add(AbilityCmdSet)
        self.add(SkillCmdSet)
        self.add(SpellCmdSet)
        self.add(InteractCmdSet)
        self.add(InfoCmdSet)
        self.add(LootCmdSet)
        self.add(RestCmdSet)
        self.add(RecallCmdSet)
        self.add(GuildCmdSet)
        self.add(EquipmentCmdSet)
        self.add(CmdDig)
        self.add(CmdLink)
        self.add(CmdTeleport)
        self.add(CmdDelRoom)
        self.add(CmdRDel)
        self.add(RoomFlagCmdSet)
        self.add(AreaCmdSet)
        self.add(AdminCmdSet)
        self.add(BuilderCmdSet)
        self.add(QuestCmdSet)
        self.add(AchievementCmdSet)
        # Override the default help command to sort the index alphabetically
        self.add(CmdHelp())


class AccountCmdSet(default_cmds.AccountCmdSet):
    """
    This is the cmdset available to the Account at all times. It is
    combined with the `CharacterCmdSet` when the Account puppets a
    Character. It holds game-account-specific commands, channel
    commands, etc.
    """

    key = "DefaultAccount"

    def at_cmdset_creation(self):
        """
        Populates the cmdset
        """
        super().at_cmdset_creation()
        #
        # any commands you add below will overload the default ones.
        #
        self.add(ContribCmdCharCreate)
        self.add(AccountOptsCmdSet)
        self.add(CmdWho)
        # Override the default help command to sort the index alphabetically
        self.add(CmdHelp())


class UnloggedinCmdSet(default_cmds.UnloggedinCmdSet):
    """
    Command set available to the Session before being logged in.  This
    holds commands like creating a new account, logging in, etc.
    """

    key = "DefaultUnloggedin"

    def at_cmdset_creation(self):
        """
        Populates the cmdset
        """
        super().at_cmdset_creation()
        #
        # any commands you add below will overload the default ones.
        #
        self.add(CmdHelp())


class SessionCmdSet(default_cmds.SessionCmdSet):
    """
    This cmdset is made available on Session level once logged in. It
    is empty by default.
    """

    key = "DefaultSession"

    def at_cmdset_creation(self):
        """
        This is the only method defined in a cmdset, called during
        its creation. It should populate the set with command instances.

        As and example we just add the empty base `Command` object.
        It prints some info.
        """
        super().at_cmdset_creation()
        #
        # any commands you add below will overload the default ones.
        #
        self.add(CmdHelp())
