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
        self.msg = MagicMock()


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

    def test_solo_gain_awards_exp(self):
        attacker = Dummy()
        attacker.db = type("DB", (), {"exp": 0})()
        victim = Dummy()
        victim.db = type("DB", (), {"exp_reward": 10})()
        with patch('world.system.state_manager.apply_regen'), \
             patch('world.system.state_manager.check_level_up'), \
             patch.object(attacker, 'msg') as mock_msg:
            engine = CombatEngine([attacker, victim], round_time=0)
            engine.queue_action(attacker, KillAction(attacker, victim))
            engine.start_round()
            engine.process_round()
            self.assertEqual(attacker.db.exp, 10)
            mock_msg.assert_called()

    def test_group_gain_splits_exp(self):
        a = Dummy()
        b = Dummy()
        for obj in (a, b):
            obj.db = type("DB", (), {"exp": 0})()
        victim = Dummy()
        victim.db = type("DB", (), {"exp_reward": 9})()
        with patch('world.system.state_manager.apply_regen'), \
             patch('world.system.state_manager.check_level_up'), \
             patch.object(a, 'msg') as msg_a, patch.object(b, 'msg') as msg_b:
            engine = CombatEngine([a, b, victim], round_time=0)
            engine.aggro[victim] = {a: 1, b: 1}
            engine.queue_action(a, KillAction(a, victim))
            engine.start_round()
            engine.process_round()
            self.assertEqual(a.db.exp, 4)
            self.assertEqual(b.db.exp, 4)
            msg_a.assert_called()
            msg_b.assert_called()

    def test_engine_stops_when_empty(self):
        a = Dummy()
        a.traits.health = MagicMock(value=a.hp)
        a.key = "dummy"
        a.tags = MagicMock()
        with patch('world.system.state_manager.apply_regen'), \
             patch('combat.combat_engine.delay') as mock_delay, \
             patch('random.randint', return_value=0):
            engine = CombatEngine([a], round_time=0)
            engine.queue_action(a, KillAction(a, a))
            engine.start_round()
            engine.process_round()
            self.assertEqual(len(engine.participants), 0)
            mock_delay.assert_not_called()

    def test_schedules_next_round(self):
        a = Dummy()
        b = Dummy()
        with patch('world.system.state_manager.apply_regen'), \
             patch('world.system.state_manager.get_effective_stat', return_value=0), \
             patch('combat.combat_actions.utils.inherits_from', return_value=False), \
             patch('combat.combat_engine.delay') as mock_delay, \
             patch('random.randint', return_value=0):
            engine = CombatEngine([a, b], round_time=0)
            engine.start_round()
            engine.process_round()
            self.assertEqual(len(engine.participants), 2)
            mock_delay.assert_called_with(1, engine.process_round)
