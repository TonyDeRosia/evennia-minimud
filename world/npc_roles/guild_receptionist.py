"""Guild receptionist role mixin."""

class GuildReceptionistRole:
    """Mixin for greeting and assisting guild members."""

    def greet_visitor(self, visitor) -> None:
        """Greet `visitor` on behalf of the guild."""
        if not visitor:
            return
        visitor.msg(f"{self.key} welcomes you to the guild hall.")
