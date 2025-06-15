from evennia.utils.test_resources import EvenniaTest


class AttackCommandTestBase(EvenniaTest):
    """Base class for attack command tests."""

    def tearDown(self):
        from combat.round_manager import CombatRoundManager

        manager = CombatRoundManager.get()
        manager.combats.clear()
        manager.combatant_to_combat.clear()
        super().tearDown()
