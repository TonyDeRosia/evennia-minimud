from unittest.mock import MagicMock, patch
import unittest

from combat.combat_engine import CombatEngine
from combat.combat_actions import Action, CombatResult


class KillAction(Action):
    def resolve(self):
        self.target.hp = 0
        return CombatResult(self.actor, self.target, "boom")


class Dummy:
    def __init__(self, hp=10, init=0):
        self.hp = hp
        self.location = MagicMock()
        self.traits = MagicMock()
        self.traits.get.return_value = MagicMock(value=init)
        self.on_enter_combat = MagicMock()
        self.on_exit_combat = MagicMock()


class TestCombatEngine(unittest.TestCase):
    def test_enter_and_exit_callbacks(self):
        a = Dummy()
        b = Dummy()
        with patch('world.system.state_manager.apply_regen'):
            engine = CombatEngine([a, b], round_time=0)
            a.on_enter_combat.assert_called()
            b.on_enter_combat.assert_called()
            engine.queue_action(a, KillAction(a, b))
            engine.start_round()
            engine.process_round()
            b.on_exit_combat.assert_called()

    def test_initiative_and_regen(self):
        a = Dummy(init=10)
        b = Dummy(init=1)
        engine = CombatEngine([a, b], round_time=0)
        with patch('world.system.state_manager.apply_regen') as mock_regen, patch('random.randint', return_value=0):
            engine.start_round()
            self.assertEqual(engine.queue[0].actor, a)
            self.assertEqual(mock_regen.call_count, 2)

    def test_aggro_tracking(self):
        a = Dummy()
        b = Dummy()
        with patch('world.system.state_manager.apply_regen'):
            engine = CombatEngine([a, b], round_time=0)
            engine.queue_action(a, KillAction(a, b))
            engine.start_round()
            engine.process_round()
            self.assertIn(a, engine.aggro.get(b, {}))
