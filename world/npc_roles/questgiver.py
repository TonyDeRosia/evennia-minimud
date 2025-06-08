"""Quest giver role mixin."""

class QuestGiverRole:
    """Mixin for offering quests to players."""

    def offer_quest(self, player, quest) -> None:
        """Offer `quest` to `player`."""
        if not player or not quest:
            return
        player.msg(f"{self.key} offers you the quest '{quest}'.")
