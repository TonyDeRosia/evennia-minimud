import unittest
from unittest.mock import MagicMock, patch, call

from combat.engine import CombatEngine
from combat.combat_actions import DefendAction, CombatResult, Action, AttackAction


class KillAction(Action):
    """Simple action that defeats its target."""

    def resolve(self):
        self.target.hp = 0
        return CombatResult(self.actor, self.target, "boom")


class Dummy:
    def __init__(self, hp=10):
        self.hp = hp
        self.location = MagicMock()
        self.traits = MagicMock()
        self.traits.get.return_value = MagicMock(value=0)
        self.tags = MagicMock()
        self.on_enter_combat = MagicMock()
        self.on_exit_combat = MagicMock()


class TestDefendAction(unittest.TestCase):
    def test_defend_resolves_before_attack(self):
        a = Dummy()
        b = Dummy()
        engine = CombatEngine([a, b], round_time=0)
        engine.queue_action(a, DefendAction(a))
        engine.queue_action(b, KillAction(b, a))
        with patch("world.system.state_manager.apply_regen"), patch(
            "random.randint", return_value=0
        ):
            engine.start_round()
            engine.process_round()
        output = a.location.msg_contents.call_args_list[0].args[0]
        messages = output.splitlines()
        self.assertTrue(any("braces" in m for m in messages))
        a.tags.add.assert_any_call("defending", category="status")



class TestAttackActionHelper(unittest.TestCase):
    def test_helper_used_for_weapon_selection(self):
        attacker = Dummy()
        defender = Dummy()
        weapon = MagicMock()
        attacker.location = defender.location
        attacker.get_attack_weapon = MagicMock(return_value=weapon)

        engine = CombatEngine([attacker, defender], round_time=0)
        engine.queue_action(attacker, AttackAction(attacker, defender))
        with patch("world.system.state_manager.apply_regen"), \
             patch("combat.combat_actions.CombatMath.check_hit", return_value=(True, "")), \
             patch("combat.combat_actions.CombatMath.calculate_damage", return_value=(5, None)) as mock_calc, \
             patch("combat.combat_actions.CombatMath.apply_critical", return_value=(5, False)), \
             patch("random.randint", return_value=0):
            engine.start_round()
            engine.process_round()

        mock_calc.assert_called_with(attacker, weapon, defender)
