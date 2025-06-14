from unittest.mock import patch
from evennia.utils.test_resources import EvenniaTest
from combat.round_manager import CombatRoundManager, CombatInstance
from combat.engine import CombatEngine


class TestCombatRoundManager(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.manager = CombatRoundManager.get()
        self.manager.instances.clear()
        self.manager.instances_by_room.clear()
        self.manager.running = False
        self.instance = self.manager.add_instance(
            self.room1, fighters=[self.char1, self.char2]
        )

    def test_tick_schedules(self):
        """Test that ticks are properly scheduled and process rounds."""
        with (
            patch("combat.round_manager.delay") as mock_delay,
            patch.object(CombatEngine, "process_round") as mock_proc,
        ):
            # Adding instance should schedule first tick
            self.manager.add_instance(self.room1)
            mock_delay.assert_called_with(self.manager.tick_delay, self.manager._tick)
            
            # First tick should process round
            mock_proc.assert_called()
            
            # Reset mocks for next tick test
            mock_delay.reset_mock()
            mock_proc.reset_mock()
            
            # Manual tick should process round and schedule next tick
            self.manager._tick()
            mock_proc.assert_called()
            mock_delay.assert_called_with(self.manager.tick_delay, self.manager._tick)

    def test_initiative_order(self):
        """Test that initiative order is correctly maintained."""
        order = []
        
        def start_round(self):
            original(self)
            order.extend([p.actor for p in self.queue])
        
        original = CombatEngine.start_round
        
        with (
            patch("combat.round_manager.delay"),
            patch("combat.combat_utils.calculate_initiative") as mock_calc,
            patch.object(CombatEngine, "start_round", new=start_round),
        ):
            # Set up initiative values: char1 gets 10, char2 gets 1
            mock_calc.side_effect = lambda c: 10 if c is self.char1 else 1
            
            self.manager.add_instance(self.room1)
            self.manager._tick()
        
        # char1 should go first (higher initiative)
        self.assertEqual(order[0], self.char1)
        self.assertEqual(order[1], self.char2)

    def test_tick_handles_deleted_script(self):
        """Test that tick gracefully handles deleted scripts without crashing."""
        with patch("combat.round_manager.delay"):
            self.manager.add_instance(self.room1)
            self.room1.pk = None
            
            # This should not raise an exception
            try:
                self.manager._tick()
            except Exception as err:
                self.fail(f"tick raised {err!r}")

    def test_tick_cleans_up_deleted_script(self):
        """Test that tick removes instances whose scripts were deleted."""
        with patch("combat.round_manager.delay"):
            inst = self.manager.add_instance(self.room1)
            self.room1.pk = None
            
            # After tick, the instance should be removed
            self.manager._tick()
            self.assertNotIn(inst, self.manager.instances)

    def test_add_instance_returns_existing(self):
        """Test that adding the same script twice returns the existing instance."""
        with patch("combat.round_manager.delay"):
            inst1 = self.manager.add_instance(self.room1)
            inst2 = self.manager.add_instance(self.room1)

            self.assertIs(inst1, inst2)
            self.assertEqual(len(self.manager.instances), 1)

    def test_add_existing_triggers_round_when_idle(self):
        """If the manager isn't running, adding an existing instance should process immediately."""
        with (
            patch("combat.round_manager.delay") as mock_delay,
            patch.object(CombatEngine, "process_round") as mock_proc,
        ):
            inst = self.manager.add_instance(self.room1)
            mock_proc.reset_mock()
            self.manager.running = False
            self.manager._next_tick_scheduled = False

            inst2 = self.manager.add_instance(self.room1)

            self.assertIs(inst, inst2)
            mock_proc.assert_called_once()
            mock_delay.assert_called_with(self.manager.tick_delay, self.manager._tick)
            self.assertTrue(self.manager.running)

    def test_remove_instance(self):
        """Test that instances can be properly removed."""
        with patch("combat.round_manager.delay"):
            self.manager.add_instance(self.room1)
            self.assertEqual(len(self.manager.instances), 1)
            
            self.manager.remove_instance(self.room1)
            self.assertEqual(len(self.manager.instances), 0)

    def test_stop_ticking_when_no_instances(self):
        """Test that ticking stops when all instances are removed."""
        with patch("combat.round_manager.delay"):
            self.manager.add_instance(self.room1)
            self.assertTrue(self.manager.running)
            
            self.manager.remove_instance(self.room1)
            self.assertFalse(self.manager.running)

    def test_combat_status_reporting(self):
        """Test that combat status is properly reported."""
        with patch("combat.round_manager.delay"):
            inst = self.manager.add_instance(self.room1)
            status = self.manager.get_combat_status()
            
            self.assertTrue(status["running"])
            self.assertEqual(status["total_instances"], 1)
            self.assertEqual(len(status["instances"]), 1)
            
            inst_status = status["instances"][0]
            self.assertEqual(inst_status["room"], str(self.room1))
            self.assertTrue(inst_status["valid"])

    def test_force_end_all_combat(self):
        """Test that all combat can be force-ended."""
        with patch("combat.round_manager.delay"):
            inst = self.manager.add_instance(self.room1)
            self.assertTrue(self.manager.running)
            
            self.manager.force_end_all_combat()
            
            self.assertEqual(len(self.manager.instances), 0)
            self.assertFalse(self.manager.running)
            self.assertTrue(inst.combat_ended)

    def test_debug_info_format(self):
        """Test that debug info is properly formatted."""
        with patch("combat.round_manager.delay"):
            self.manager.add_instance(self.room1)
            debug_info = self.manager.debug_info()
            
            self.assertIn("Combat Manager Status:", debug_info)
            self.assertIn("Running: True", debug_info)
            self.assertIn("Active Instances: 1", debug_info)
            self.assertIn("Instance 1:", debug_info)

    def test_singleton_pattern(self):
        """Test that CombatRoundManager follows singleton pattern."""
        manager1 = CombatRoundManager.get()
        manager2 = CombatRoundManager.get()
        
        self.assertIs(manager1, manager2)

    def test_invalid_script_cleanup(self):
        """Test that invalid scripts are cleaned up during tick."""
        with patch("combat.round_manager.delay"):
            inst = self.manager.add_instance(self.room1)
            
            # Make script invalid by removing its pk
            self.room1.pk = None
            
            self.manager._tick()
            self.assertNotIn(inst, self.manager.instances)

    def test_no_active_fighters_cleanup(self):
        """Test that instances with no active fighters are cleaned up."""
        with (
            patch("combat.round_manager.delay"),
            patch.object(self.char1.db, "hp", 0),  # Make char1 dead
            patch.object(self.char2.db, "hp", 0),  # Make char2 dead
        ):
            inst = self.manager.add_instance(self.room1)
            
            self.manager._tick()
            self.assertNotIn(inst, self.manager.instances)
            self.assertTrue(inst.combat_ended)

    def test_add_combatant_raises_without_engine(self):
        """add_combatant should raise RuntimeError if engine is missing."""
        inst = CombatInstance(self.room1, None)
        with self.assertRaises(RuntimeError):
            inst.add_combatant(self.char1)
