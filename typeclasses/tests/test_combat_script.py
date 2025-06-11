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

    def test_remove_all_combatants_preserves_team_structure(self):
        """Removing everyone should leave two empty team lists."""
        from typeclasses.scripts import CombatScript

        self.room1.scripts.add(CombatScript, key="combat")
        script = self.room1.scripts.get("combat")[0]
        script.add_combatant(self.char1, enemy=self.char2)

        script.delete = MagicMock()

        for fighter in list(script.fighters):
            script.remove_combatant(fighter)

        self.assertEqual(script.db.teams, [[], []])
        script.check_victory()
