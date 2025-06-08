"""Guildmaster role mixin."""

class GuildmasterRole:
    """Mixin for guild management behavior."""

    def manage_guild(self, caller) -> None:
        """Handle generic guild management interaction."""
        if not caller:
            return
        caller.msg(f"{self.key} discusses guild matters with you.")
