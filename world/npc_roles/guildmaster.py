"""Guildmaster role mixin."""

class GuildmasterRole:
    """Mixin for guild management behavior."""

    def manage_guild(self, caller) -> None:
        """Add ``caller`` to this guild or update their rank."""
        if not caller:
            return

        from world.guilds import find_guild, update_guild, auto_promote

        guild_name = self.db.guild
        if not guild_name:
            caller.msg("This guildmaster has no guild.")
            return

        idx, guild = find_guild(guild_name)
        if guild is None:
            caller.msg("The guild is not recognized.")
            return

        charid = str(caller.id)
        gp_map = caller.db.guild_points or {}
        if charid not in guild.members:
            guild.members[charid] = 0
            caller.db.guild = guild_name
            gp_map[guild_name] = 0
            caller.db.guild_points = gp_map
            update_guild(idx, guild)
            caller.msg(f"{self.key} inducts you into {guild_name}.")
        else:
            guild.members[charid] = guild.members.get(charid, 0) + 1
            gp_map[guild_name] = guild.members[charid]
            caller.db.guild_points = gp_map
            update_guild(idx, guild)
            auto_promote(caller, guild)
            caller.msg(f"{self.key} recognizes your service to {guild_name}.")
