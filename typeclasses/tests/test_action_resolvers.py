import unittest
from unittest.mock import MagicMock, patch

from combat.engine import CombatEngine
from combat.combat_actions import CombatResult, Action
from combat.action_resolvers import resolve_combat_result


class Dummy:
    def __init__(self, hp=10, key="dummy"):
        self.hp = hp
        self.key = key
        self.location = MagicMock()
        self.on_exit_combat = MagicMock()
        self.at_defeat = MagicMock()
        self.pk = 1
        self.engine = None

    def at_damage(self, attacker, amount, damage_type=None):
        self.hp = max(self.hp - amount, 0)
        return amount

    def on_death(self, attacker):
        if self.engine:
            self.engine.award_experience(attacker, self)


class DamageAction(Action):
    def resolve(self):
        return CombatResult(self.actor, self.target, "", damage=5)


class TestActionResolver(unittest.TestCase):
    def _setup(self, attacker_hp=10, defender_hp=10):
        attacker = Dummy(attacker_hp, key="attacker")
        defender = Dummy(defender_hp, key="defender")
        engine = CombatEngine([attacker, defender], round_time=0)
        attacker.engine = engine
        defender.engine = engine
        return engine, attacker, defender

    def test_damage_application(self):
        engine, attacker, defender = self._setup()
        participant = engine.turn_manager.participants[0]
        result = CombatResult(attacker, defender, "", damage=5)
        totals = {}

        with patch("combat.action_resolvers.format_combat_message", return_value="hit"), \
             patch.object(engine.processor, "_buffer_message") as mock_buf, \
             patch.object(engine.processor, "handle_defeat") as mock_defeat:
            resolve_combat_result(engine.processor, participant, result, totals)

        self.assertEqual(defender.hp, 5)
        mock_defeat.assert_not_called()
        mock_buf.assert_called_once()
        self.assertEqual(totals[attacker], 5)

    def test_defeat_triggers_xp_award(self):
        engine, attacker, defender = self._setup(defender_hp=5)
        participant = engine.turn_manager.participants[0]
        result = CombatResult(attacker, defender, "", damage=5)
        totals = {}

        def simple_defeat(t, a):
            t.on_death(a)

        engine.processor.handle_defeat = simple_defeat

        with patch.object(engine, "award_experience") as mock_xp:
            resolve_combat_result(engine.processor, participant, result, totals)

        self.assertEqual(defender.hp, 0)
        mock_xp.assert_called_once_with(attacker, defender)


if __name__ == "__main__":
    unittest.main()
