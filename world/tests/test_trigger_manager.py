from unittest.mock import MagicMock, patch
import unittest
from world.triggers import TriggerManager


class Dummy:
    def __init__(self):
        self.db = type("DB", (), {})()
        self.db.triggers = {}
        self.execute_cmd = MagicMock()
        self.traits = type("Traits", (), {})()
        self.traits.health = type("Hp", (), {"value": 100, "max": 100})()
        self.in_combat = False


class TestTriggerManager(unittest.TestCase):
    def setUp(self):
        self.obj = Dummy()

    @patch("world.triggers.randint", return_value=1)
    def test_percent_condition(self, mock_rand):
        self.obj.db.triggers["on_timer"] = [{"percent": 50, "response": "say hi"}]
        TriggerManager(self.obj).check("on_timer")
        self.obj.execute_cmd.assert_called_with("say hi")

    def test_combat_condition(self):
        self.obj.db.triggers["on_attack"] = [{"combat": True, "response": "say fight"}]
        TriggerManager(self.obj).check("on_attack")
        self.obj.execute_cmd.assert_not_called()
        self.obj.execute_cmd.reset_mock()
        self.obj.in_combat = True
        TriggerManager(self.obj).check("on_attack")
        self.obj.execute_cmd.assert_called_with("say fight")

    def test_bribe_condition(self):
        self.obj.db.triggers["on_bribe"] = [{"bribe": 10, "response": "say thanks"}]
        TriggerManager(self.obj).check("on_bribe", amount=5)
        self.obj.execute_cmd.assert_not_called()
        self.obj.execute_cmd.reset_mock()
        TriggerManager(self.obj).check("on_bribe", amount=15)
        self.obj.execute_cmd.assert_called_with("say thanks")

    def test_hp_pct_condition(self):
        self.obj.db.triggers["on_attack"] = [{"hp_pct": 50, "response": "say hurt"}]
        self.obj.traits.health.value = 60
        TriggerManager(self.obj).check("on_attack")
        self.obj.execute_cmd.assert_not_called()
        self.obj.execute_cmd.reset_mock()
        self.obj.traits.health.value = 40
        TriggerManager(self.obj).check("on_attack")
        self.obj.execute_cmd.assert_called_with("say hurt")


if __name__ == "__main__":
    unittest.main()
