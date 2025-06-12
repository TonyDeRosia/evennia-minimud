from unittest.mock import patch
from evennia.utils.test_resources import EvenniaTest

from typeclasses.scripts import CombatScript
from combat.round_manager import CombatRoundManager
from combat.combat_engine import CombatEngine


class TestCombatRoundManager(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.room1.scripts.add(CombatScript, key="combat")
        self.script = self.room1.scripts.get("combat")[0]
        self.script.add_combatant(self.char1, enemy=self.char2)
        self.manager = CombatRoundManager.get()
        self.manager.instances.clear()
        self.manager.running = False

    def test_tick_schedules(self):
        with patch("combat.round_manager.delay") as mock_delay:
            self.manager.add_instance(self.script)
            mock_delay.assert_called_with(1, self.manager.tick)
            mock_delay.reset_mock()
            with patch.object(CombatEngine, "process_round") as mock_proc:
                self.manager.tick()
                mock_proc.assert_called()
            mock_delay.assert_called_with(1, self.manager.tick)

    def test_initiative_order(self):
        order = []

        def start_round(self):
            original(self)
            order.extend([p.actor for p in self.queue])

        original = CombatEngine.start_round
        with patch("combat.round_manager.delay"), \
             patch("combat.combat_utils.calculate_initiative") as mock_calc, \
             patch.object(CombatEngine, "start_round", new=start_round):
            mock_calc.side_effect = lambda c: 10 if c is self.char1 else 1
            self.manager.add_instance(self.script)
            self.manager.tick()

        self.assertEqual(order[0], self.char1)
        self.assertEqual(order[1], self.char2)
