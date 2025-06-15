from evennia.utils.test_resources import EvenniaTest


class AttackCommandTestBase(EvenniaTest):
    """Base class for attack command tests."""

    def tearDown(self):
        from combat.round_manager import CombatRoundManager

        manager = CombatRoundManager.get()
        manager.combats.clear()
        manager.combatant_to_combat.clear()
        super().tearDown()

    def _assert_combat_targets_set(self, attacker, target):
        """Assert that the two combatants have each other set as targets."""
        self.assertEqual(attacker.db.combat_target, target)
        self.assertEqual(target.db.combat_target, attacker)

    def _assert_combat_initiated(self, actor=None):
        """Assert that combat has started and an AttackAction is queued."""
        from combat.round_manager import CombatRoundManager
        from combat.combat_actions import AttackAction

        manager = CombatRoundManager.get()
        self.assertTrue(manager.combats)

        engine = list(manager.combats.values())[0].engine
        if actor is None:
            queued = [
                act
                for p in engine.participants
                for act in p.next_action
                if isinstance(act, AttackAction)
            ]
        else:
            queued = [
                act
                for p in engine.participants
                if p.actor is actor
                for act in p.next_action
                if isinstance(act, AttackAction)
            ]
        self.assertTrue(queued)
