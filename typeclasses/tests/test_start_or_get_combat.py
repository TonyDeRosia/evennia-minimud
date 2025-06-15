from unittest.mock import patch, MagicMock
from evennia.utils.test_resources import EvenniaTest


class TestStartOrGetCombat(EvenniaTest):
    def test_returns_existing_instance(self):
        from combat.combat_utils import start_or_get_combat

        with patch("combat.round_manager.CombatRoundManager.get") as mock_get, patch(
            "combat.combat_utils.maybe_start_combat"
        ) as mock_start:
            manager = MagicMock()
            inst = MagicMock()
            mock_get.return_value = manager
            manager.get_combatant_combat.return_value = inst

            result = start_or_get_combat(self.char1, self.char2)

            self.assertIs(result, inst)
            mock_start.assert_not_called()

    def test_starts_new_combat_when_none(self):
        from combat.combat_utils import start_or_get_combat

        with patch("combat.round_manager.CombatRoundManager.get") as mock_get, patch(
            "combat.combat_utils.maybe_start_combat", return_value="inst"
        ) as mock_start:
            manager = MagicMock()
            mock_get.return_value = manager
            manager.get_combatant_combat.return_value = None

            result = start_or_get_combat(self.char1, self.char2)

            mock_start.assert_called_with(self.char1, self.char2)
            self.assertEqual(result, "inst")

