"""Combat trainer role mixin."""

class CombatTrainerRole:
    """Mixin for training combat techniques."""

    def spar(self, trainee) -> None:
        """Spar with `trainee` to improve their skills."""
        if not trainee:
            return
        trainee.msg(f"{self.key} spars with you, honing your abilities.")
