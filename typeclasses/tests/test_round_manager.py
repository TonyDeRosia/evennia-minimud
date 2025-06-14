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
            mock_delay.assert_called_with(self.manager.tick_delay, self.manager._tick)
            mock_delay.reset_mock()
            with patch.object(CombatEngine, "process_round") as mock_proc:
                self.manager._tick()
                mock_proc.assert_called()
            mock_delay.assert_called_with(self.manager.tick_delay, self.manager._tick)

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
            self.manager._tick()

        self.assertEqual(order[0], self.char1)
        self.assertEqual(order[1], self.char2)

    def test_tick_handles_deleted_script(self):
        with patch("combat.round_manager.delay"):
            self.manager.add_instance(self.script)
            self.script.delete()
            try:
                self.manager._tick()
            except Exception as err:  # pragma: no cover - fail fast if exception
                self.fail(f"tick raised {err!r}")

    def test_tick_cleans_up_deleted_script(self):
        """Tick should remove instances whose scripts were deleted."""
        with patch("combat.round_manager.delay"):
            inst = self.manager.add_instance(self.script)
            self.script.delete()
            self.manager._tick()
            self.assertNotIn(inst, self.manager.instances)
