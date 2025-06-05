from evennia import CmdSet, search_object
from evennia.utils.evtable import EvTable

from .command import Command
from world.guilds import GUILDS, get_rank_title


class CmdGuild(Command):
    """
    Show information about your current guild.

    Usage:
        guild

    Example:
        guild
    """

    key = "guild"
    aliases = ("/guild",)
    help_category = "general"

    def func(self):
        caller = self.caller
        guild = caller.db.guild
        honor = caller.db.guild_honor or 0
        if not guild:
            self.msg("You are not a member of any guild.")
            return
        info = GUILDS.get(guild, {})
        crest = info.get("crest", "")
        motd = info.get("motd", "")
        rank = get_rank_title(guild, honor)
        self.msg(f"|w{guild}|n {crest}")
        self.msg(f"Rank: {rank}")
        self.msg(f"Honor: {honor}")
        if motd:
            self.msg(motd)


class CmdGuildWho(Command):
    """
    List members of your guild and their status.

    Usage:
        guildwho

    Example:
        guildwho
    """

    key = "guildwho"
    help_category = "general"

    def func(self):
        caller = self.caller
        guild = caller.db.guild
        if not guild:
            self.msg("You are not a member of any guild.")
            return
        try:
            from typeclasses.characters import PlayerCharacter
            candidates = PlayerCharacter.objects.all()
        except Exception:
            candidates = search_object("*")
        members = [c for c in candidates if c.db.guild == guild]
        if not members:
            self.msg("No members found.")
            return
        table = EvTable("Name", "Rank", "Status", border="none")
        for mem in members:
            status = "Online" if mem.sessions.count() else "Offline"
            rank = get_rank_title(guild, mem.db.guild_honor or 0)
            table.add_row(mem.key, rank, status)
        self.msg(str(table))


class GuildCmdSet(CmdSet):
    key = "Guild CmdSet"

    def at_cmdset_creation(self):
        super().at_cmdset_creation()
        self.add(CmdGuild)
        self.add(CmdGuildWho)

