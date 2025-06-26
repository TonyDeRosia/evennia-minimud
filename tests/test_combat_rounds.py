import unittest
from unittest.mock import MagicMock, patch

from combat.round_manager import CombatRoundManager, CombatInstance
from combat.combat_actions import AttackAction


class Dummy:
    def __init__(self, hp=10):
        self.hp = hp
        self.key = "dummy"
        self.location = MagicMock()
        self.traits = MagicMock()
        self.traits.get.return_value = MagicMock(value=0)
        self.traits.health = MagicMock(value=hp, max=hp)
        self.db = type("DB", (), {})()
        self.on_enter_combat = MagicMock()
        self.on_exit_combat = MagicMock()
        self.msg = MagicMock()

    def at_damage(self, attacker, amount, damage_type=None):
        self.hp = max(self.hp - amount, 0)
        self.traits.health.value = self.hp
        return amount


class TestCombatRounds(unittest.TestCase):
    def setUp(self):
        self.manager = CombatRoundManager.get()
        self.manager.force_end_all_combat()

    def test_attack_damage_and_defeat_end_combat(self):
        attacker = Dummy()
        defender = Dummy(hp=1)

        with patch.object(CombatInstance, "start"), patch.object(
            CombatInstance, "_schedule_tick"
        ):
            inst = self.manager.start_combat([attacker, defender])

        engine = inst.engine
        engine.queue_action(attacker, AttackAction(attacker, defender))

        with (
            patch("combat.combat_actions.CombatMath.check_hit", return_value=(True, "")),
            patch("combat.combat_actions.CombatMath.calculate_damage", return_value=(1, None, None)),
            patch("combat.combat_actions.CombatMath.apply_critical", return_value=(1, False)),
            patch("world.system.state_manager.apply_regen"),
            patch("world.system.state_manager.get_effective_stat", return_value=0),
            patch("combat.engine.damage_processor.delay"),
            patch("random.randint", return_value=0),
            patch.object(engine.processor, "handle_defeat", wraps=engine.processor.handle_defeat) as mock_defeat,
        ):
            inst.process_round()

        self.assertEqual(defender.hp, 0)
        self.assertTrue(mock_defeat.called)
        self.assertTrue(inst.combat_ended)
        self.assertIsNone(self.manager.get_combatant_combat(defender))


if __name__ == "__main__":
    unittest.main()
