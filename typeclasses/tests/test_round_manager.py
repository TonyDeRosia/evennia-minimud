from unittest.mock import patch
from evennia.utils.test_resources import EvenniaTest
from combat.round_manager import CombatRoundManager, CombatInstance
from combat.engine import CombatEngine


class TestCombatRoundManager(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.manager = CombatRoundManager.get()
        self.manager.combats.clear()
        self.manager.combatant_to_combat.clear()
        with patch.object(CombatInstance, "start"):
            self.instance = self.manager.create_combat(combatants=[self.char1, self.char2])

    def test_create_schedules_tick(self):
        with patch.object(CombatInstance, "start") as mock_sched:
            self.manager.create_combat(combatants=[self.char1, self.char2])
            mock_sched.assert_called_once_with()

    def test_tick_processes_and_reschedules(self):
        with patch.object(CombatInstance, "_schedule_tick") as mock_sched, patch.object(CombatEngine, "process_round") as mock_proc:
            inst = self.manager.create_combat(combatants=[self.char1, self.char2])
            mock_sched.reset_mock()
            inst._tick()
            mock_proc.assert_called_once()
            mock_sched.assert_called_once()

    def test_instances_schedule_independently(self):
        with patch.object(CombatInstance, "start") as mock_sched:
            self.manager.create_combat(combatants=[self.char1, self.char2])
            self.manager.create_combat(combatants=[self.char2, self.char1])
            self.assertEqual(mock_sched.call_count, 2)

    def test_start_combat_reuses_instance(self):
        with patch.object(CombatInstance, "start"):
            inst1 = self.manager.start_combat([self.char1, self.char2])
            inst2 = self.manager.start_combat([self.char1])
        self.assertIs(inst1, inst2)
        self.assertEqual(len(self.manager.combats), 1)

    def test_remove_instance(self):
        self.manager.remove_combat(self.instance.combat_id)
        self.assertEqual(len(self.manager.combats), 0)

    def test_force_end_all_combat(self):
        with patch.object(CombatInstance, "start"):
            inst = self.manager.create_combat(combatants=[self.char1])
        self.manager.force_end_all_combat()
        self.assertTrue(inst.combat_ended)
        self.assertFalse(self.manager.combats)

    def test_debug_info_format(self):
        info = self.manager.debug_info()
        self.assertIn("Combat Manager Status:", info)
        self.assertIn("Active Instances:", info)

    def test_end_combat_clears_flags(self):
        self.char1.db.combat_target = self.char2
        self.char2.db.combat_target = self.char1

        self.instance.end_combat("done")

        self.assertFalse(self.char1.db.in_combat)
        self.assertIsNone(getattr(self.char1.db, "combat_target", None))
        self.assertFalse(self.char2.db.in_combat)
        self.assertIsNone(getattr(self.char2.db, "combat_target", None))

    def test_start_combat_merges_instances(self):
        with patch.object(CombatInstance, "start"):
            extra = self.manager.create_combat(combatants=[self.char3])

        with patch.object(CombatInstance, "start"):
            merged = self.manager.start_combat([self.char1, self.char3])

        self.assertIs(merged, self.instance)
        self.assertEqual(len(self.manager.combats), 1)
        self.assertIn(self.char1, merged.combatants)
        self.assertIn(self.char2, merged.combatants)
        self.assertIn(self.char3, merged.combatants)
        self.assertIs(self.manager.get_combatant_combat(self.char3), merged)
        self.assertTrue(extra.combat_ended)

