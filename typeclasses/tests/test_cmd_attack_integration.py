from unittest.mock import MagicMock, patch
from django.test import override_settings
from evennia.utils import create
from evennia.utils.test_resources import EvenniaTest

from commands.combat import CombatCmdSet
from combat.round_manager import CombatRoundManager, CombatInstance
from combat.combat_actions import AttackAction
from combat.engine.combat_engine import CombatEngine
from typeclasses.npcs import CombatNPC


@override_settings(DEFAULT_HOME=None)
class TestCmdAttackIntegration(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.char1.msg = MagicMock()
        self.char1.cmdset.add_default(CombatCmdSet)
        self.room1.msg_contents = MagicMock()

    def test_cmd_attack_processes_first_round(self):
        npc = create.create_object(CombatNPC, key="mob", location=self.room1)
        npc.traits.health.current = 5

        manager = CombatRoundManager.get()
        manager.force_end_all_combat()

        with (
            patch.object(manager, "start_combat", wraps=manager.start_combat) as mock_start,
            patch.object(CombatInstance, "start"),
            patch.object(CombatEngine, "queue_action", wraps=CombatEngine.queue_action) as mock_queue,
            patch.object(AttackAction, "resolve", wraps=AttackAction.resolve) as mock_resolve,
            patch("combat.combat_actions.CombatMath.check_hit", return_value=(True, "")),
            patch("combat.combat_actions.CombatMath.calculate_damage", return_value=(1, None)),
            patch("combat.combat_actions.CombatMath.apply_critical", return_value=(1, False)),
            patch("combat.engine.damage_processor.delay"),
            patch("world.system.state_manager.apply_regen"),
            patch("world.system.state_manager.get_effective_stat", return_value=0),
            patch("random.randint", return_value=0),
        ):
            self.char1.execute_cmd("attack mob")

        self.assertTrue(mock_start.called)
        self.assertTrue(any(isinstance(c.args[1], AttackAction) for c in mock_queue.call_args_list))
        instance = manager.get_combatant_combat(self.char1)
        self.assertEqual(instance.round_number, 1)
        self.assertEqual(npc.traits.health.current, 4)
        self.assertTrue(self.room1.msg_contents.called)
