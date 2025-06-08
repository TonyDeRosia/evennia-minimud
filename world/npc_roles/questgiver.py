"""Quest giver role mixin."""

class QuestGiverRole:
    """Mixin for offering quests to players."""

    def offer_quest(self, player, quest) -> None:
        """Grant ``quest`` to ``player`` if possible."""
        if not player or not quest:
            return

        from world.quests import QuestManager, normalize_quest_key

        quest_key = normalize_quest_key(quest)
        _, qobj = QuestManager.find(quest_key)
        if not qobj:
            return

        active = player.db.active_quests or {}
        completed = player.db.completed_quests or []
        if quest_key in active or (not qobj.repeatable and quest_key in completed):
            player.msg(f"{self.key} has no new quests for you.")
            return

        active[quest_key] = {"progress": 0}
        player.db.active_quests = active
        title = qobj.title or quest_key
        player.msg(f"{self.key} offers you the quest '{title}'.")
