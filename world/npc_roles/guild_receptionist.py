"""Guild receptionist role mixin."""

class GuildReceptionistRole:
    """Mixin for greeting and assisting guild members."""

    def greet_visitor(self, visitor) -> None:
        """Provide a greeting or directions to ``visitor``."""
        if not visitor:
            return

        guild = self.db.guild
        if guild and visitor.db.guild == guild:
            visitor.msg(f"{self.key} says, 'Welcome back to {guild}, {visitor.key}.'")
        elif guild:
            visitor.msg(f"{self.key} says, 'Greetings traveler. The {guild} hall is this way.'")
        else:
            visitor.msg(f"{self.key} welcomes you to the guild hall.")
