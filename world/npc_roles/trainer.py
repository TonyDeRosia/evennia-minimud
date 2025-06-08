"""Trainer role mixin."""

class TrainerRole:
    """Mixin providing simple trainer behavior."""

    def train(self, trainee, skill: str) -> None:
        """Handle training `trainee` in a `skill`."""
        if not trainee:
            return
        trainee.msg(f"{self.key} trains you in {skill}.")
