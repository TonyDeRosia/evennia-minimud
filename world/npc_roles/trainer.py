"""Trainer role mixin."""

class TrainerRole:
    """Mixin providing simple trainer behavior."""

    def train(self, trainee, skill: str) -> None:
        """Improve ``trainee``'s ``skill`` in exchange for experience."""
        if not trainee or not skill:
            return

        from commands.skills import SKILL_DICT
        from world.system import stat_manager

        xp = int(trainee.db.exp or 0)
        if xp <= 0:
            trainee.msg("You lack the experience to train right now.")
            return

        trait = trainee.traits.get(skill)
        if not trait:
            trait = trainee.traits.add(
                skill,
                trait_type="counter",
                min=0,
                max=100,
                base=0,
                stat=SKILL_DICT.get(skill),
            )
            trait.proficiency = 25

        trainee.db.exp = xp - 1
        trait.base += 1
        stat_manager.refresh_stats(trainee)
        trainee.msg(f"{self.key} trains you in {skill}.")
