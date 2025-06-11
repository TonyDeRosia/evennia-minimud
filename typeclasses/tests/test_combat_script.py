from unittest.mock import MagicMock
from evennia.utils.test_resources import EvenniaTest


class TestCombatVictory(EvenniaTest):
    def test_victory_handles_missing_teams(self):
        from typeclasses.scripts import CombatScript

        self.room1.scripts.add(CombatScript, key="combat")
        script = self.room1.scripts.get("combat")[0]
        script.add_combatant(self.char1, enemy=self.char2)

        # mark target as defeated
        self.char2.tags.add("dead", category="status")

        # corrupt the team data
        script.db.teams = None
        script.ndb.teams = None
        script.delete = MagicMock()

        # should not raise and should attempt to delete the script
        script.check_victory()
        script.delete.assert_called()
