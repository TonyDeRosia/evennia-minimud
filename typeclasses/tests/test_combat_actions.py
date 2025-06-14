import unittest
from unittest.mock import MagicMock, patch, call

from combat.engine import CombatEngine
from combat.combat_actions import DefendAction, CombatResult, Action


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
        messages = [call.args[0] for call in a.location.msg_contents.call_args_list]
        self.assertIn("braces", messages[0])
        a.tags.add.assert_any_call("defending", category="status")


