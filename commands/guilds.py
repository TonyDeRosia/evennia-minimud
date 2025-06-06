from evennia import CmdSet, search_object
from evennia.utils.evtable import EvTable
from evennia.utils.utils import make_iter
from utils.roles import is_guildmaster, is_receptionist

from .command import Command
from world.guilds import (
    Guild,
    get_guilds,
    save_guild,
    update_guild,
    find_guild,
    auto_promote,
)


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
    help_category = "General"

    def func(self):
        caller = self.caller
        guild = caller.db.guild
        gp_map = caller.db.guild_points or {}
        points = gp_map.get(guild, 0)
        if not guild:
            self.msg("You are not a member of any guild.")
            return
        _, gobj = find_guild(guild)
        desc = gobj.desc if gobj else ""
        rank = caller.db.guild_rank or ""
        self.msg(f"|w{guild}|n")
        self.msg(f"Rank: {rank}")
        self.msg(f"Guild Points: {points}")
        if desc:
            self.msg(desc)


class CmdGuildWho(Command):
    """
    List members of your guild and their status.

    Usage:
        guildwho

    Example:
        guildwho
    """

    key = "gwho"
    aliases = ("guildwho",)
    help_category = "General"

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
        table = EvTable("Name", "Rank", "GP", "Status", border="none")
        for mem in members:
            status = "Online" if mem.sessions.count() else "Offline"
            rank = mem.db.guild_rank or ""
            gp_map = mem.db.guild_points or {}
            pts = gp_map.get(guild, 0)
            table.add_row(mem.key, rank, str(pts), status)
        self.msg(str(table))


class CmdGCreate(Command):
    """Create a new guild and register it."""

    key = "gcreate"
    locks = "cmd:all()"
    help_category = "Building"

    def func(self):
        if not is_guildmaster(self.caller):
            self.msg("You do not have permission to do that.")
            return
        if not self.args:
            self.msg("Usage: gcreate <name>")
            return
        name = self.args.strip()
        _, existing = find_guild(name)
        if existing:
            self.msg("Guild already exists.")
            return
        guild = Guild(name=name)
        save_guild(guild)
        self.msg(f"Guild '{name}' created.")


class CmdGRank(Command):
    """Manage guild rank titles."""

    key = "grank"
    locks = "cmd:all()"
    help_category = "Building"

    def func(self):
        if not is_guildmaster(self.caller):
            self.msg("You do not have permission to do that.")
            return
        if not self.args:
            self.msg("Usage: grank add/remove/list <guild> [level title]")
            return
        parts = self.args.split(None, 2)
        if len(parts) < 2:
            self.msg("Usage: grank add/remove/list <guild> [level title]")
            return
        action, guild_name = parts[0], parts[1]
        idx, guild = find_guild(guild_name)
        if guild is None:
            self.msg("Unknown guild.")
            return
        action = action.lower()
        if action == "list":
            if not guild.ranks:
                self.msg("No ranks defined.")
                return
            table = EvTable("Level", "Title", border="none")
            for lvl, title in guild.ranks:
                table.add_row(str(lvl), title)
            self.msg(str(table))
            return
        if len(parts) < 3:
            self.msg("Usage: grank add/remove <guild> <level> [title]")
            return
        rest = parts[2]
        if action == "add":
            lvl_title = rest.split(None, 1)
            if len(lvl_title) < 2 or not lvl_title[0].isdigit():
                self.msg("Usage: grank add <guild> <level> <title>")
                return
            level = int(lvl_title[0])
            title = lvl_title[1]
            guild.ranks.append((level, title))
            guild.ranks.sort(key=lambda r: r[0])
            update_guild(idx, guild)
            self.msg("Rank added.")
        elif action == "remove":
            if not rest.isdigit():
                self.msg("Usage: grank remove <guild> <level>")
                return
            level = int(rest)
            guild.ranks = [r for r in guild.ranks if r[0] != level]
            update_guild(idx, guild)
            self.msg("Rank removed.")
        else:
            self.msg("Usage: grank add/remove/list <guild> ...")


class CmdGSetHome(Command):
    """Set the home location for a guild."""

    key = "gsethome"
    locks = "cmd:all()"
    help_category = "Building"

    def func(self):
        if not is_guildmaster(self.caller):
            self.msg("You do not have permission to do that.")
            return
        if not self.args:
            self.msg("Usage: gsethome <guild>")
            return
        guild_name = self.args.strip()
        idx, guild = find_guild(guild_name)
        if guild is None:
            self.msg("Unknown guild.")
            return
        if not self.caller.location:
            self.msg("No location to set as home.")
            return
        guild.home = self.caller.location.id
        update_guild(idx, guild)
        self.msg(f"Home for {guild.name} set to {self.caller.location.key}.")


class CmdGDesc(Command):
    """Set the description of a guild."""

    key = "gdesc"
    locks = "cmd:all()"
    help_category = "Building"

    def func(self):
        if not is_guildmaster(self.caller):
            self.msg("You do not have permission to do that.")
            return
        if not self.args:
            self.msg("Usage: gdesc <guild> <description>")
            return
        parts = self.args.split(None, 1)
        if len(parts) < 2:
            self.msg("Usage: gdesc <guild> <description>")
            return
        guild_name, desc = parts
        idx, guild = find_guild(guild_name)
        if guild is None:
            self.msg("Unknown guild.")
            return
        guild.desc = desc
        update_guild(idx, guild)
        self.msg(f"Description for {guild.name} updated.")


class CmdGJoin(Command):
    """Request to join a guild."""

    key = "gjoin"
    help_category = "General"

    def func(self):
        if not self.args:
            self.msg("Usage: gjoin <guild>")
            return
        if self.caller.db.guild:
            self.msg("You are already in a guild.")
            return
        guild_name = self.args.strip()
        _, guild = find_guild(guild_name)
        if guild is None:
            self.msg("Unknown guild.")
            return
        self.caller.db.guild_request = guild.name
        self.msg(f"You request to join {guild.name}.")


class CmdGAccept(Command):
    """Accept a player's join request."""

    key = "gaccept"
    help_category = "General"

    def func(self):
        if not is_guildmaster(self.caller):
            self.msg("You do not have permission to do that.")
            return
        if not self.args:
            self.msg("Usage: gaccept <player>")
            return
        guild = self.caller.db.guild
        if not guild:
            self.msg("You are not in a guild.")
            return
        target = self.caller.search(self.args.strip(), global_search=True)
        if not target:
            return
        if target.db.guild:
            self.msg("That player is already in a guild.")
            return
        if target.db.guild_request != guild:
            self.msg(f"{target.key} has not requested to join {guild}.")
            return
        idx, gobj = find_guild(guild)
        if gobj is None:
            self.msg("Unknown guild.")
            return
        gobj.members[str(target.id)] = 0
        update_guild(idx, gobj)
        target.db.guild = guild
        gp_map = target.db.guild_points or {}
        gp_map[guild] = 0
        target.db.guild_points = gp_map
        target.db.guild_rank = ""
        target.db.guild_request = None
        self.msg(f"{target.key} is now a member of {guild}.")


class _BaseAdjustHonor(Command):
    locks = "cmd:all()"
    help_category = "General"

    def adjust(self, amount: int):
        if not (is_guildmaster(self.caller) or is_receptionist(self.caller)):
            self.msg("You do not have permission to do that.")
            return
        if not self.args:
            self.msg(f"Usage: {self.key} <player> [amount]")
            return
        guild = self.caller.db.guild
        if not guild:
            self.msg("You are not in a guild.")
            return
        parts = self.args.split(None, 1)
        target = self.caller.search(parts[0], global_search=True)
        if not target:
            return
        if target.db.guild != guild:
            self.msg("They are not in your guild.")
            return
        amt = 1
        if len(parts) > 1 and parts[1].lstrip("-+").isdigit():
            amt = int(parts[1])
        gp_map = target.db.guild_points or {}
        points = gp_map.get(guild, 0)
        points += amount * amt
        if points < 0:
            points = 0
        gp_map[guild] = points
        target.db.guild_points = gp_map
        idx, gobj = find_guild(guild)
        if gobj:
            gobj.members[str(target.id)] = points
            update_guild(idx, gobj)
            auto_promote(target, gobj)
        self.msg(f"{target.key} now has {points} guild points.")


class CmdGPromote(_BaseAdjustHonor):
    """Increase a member's guild points."""

    key = "gpromote"

    def func(self):
        self.adjust(1)


class CmdGDemote(_BaseAdjustHonor):
    """Decrease a member's guild points."""

    key = "gdemote"

    def func(self):
        self.adjust(-1)


class CmdGKick(Command):
    """Remove a member from your guild."""

    key = "gkick"
    help_category = "General"

    def func(self):
        if not is_guildmaster(self.caller):
            self.msg("You do not have permission to do that.")
            return
        if not self.args:
            self.msg("Usage: gkick <player>")
            return
        guild = self.caller.db.guild
        if not guild:
            self.msg("You are not in a guild.")
            return
        target = self.caller.search(self.args.strip(), global_search=True)
        if not target:
            return
        if target.db.guild != guild:
            self.msg("They are not in your guild.")
            return
        idx, gobj = find_guild(guild)
        if gobj and str(target.id) in gobj.members:
            del gobj.members[str(target.id)]
            update_guild(idx, gobj)
        target.db.guild = ""
        gp_map = target.db.guild_points or {}
        gp_map.pop(guild, None)
        target.db.guild_points = gp_map
        target.db.guild_rank = ""
        target.db.guild_request = None
        self.msg(f"{target.key} has been kicked from {guild}.")


class GuildCmdSet(CmdSet):
    key = "Guild CmdSet"

    def at_cmdset_creation(self):
        super().at_cmdset_creation()
        self.add(CmdGuild)
        self.add(CmdGuildWho)
        self.add(CmdGCreate)
        self.add(CmdGRank)
        self.add(CmdGSetHome)
        self.add(CmdGDesc)
        self.add(CmdGJoin)
        self.add(CmdGAccept)
        self.add(CmdGPromote)
        self.add(CmdGDemote)
        self.add(CmdGKick)

