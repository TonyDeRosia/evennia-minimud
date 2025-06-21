import unittest
from unittest.mock import MagicMock, patch

from django.test import override_settings
from evennia.utils import create
from evennia.utils.test_resources import EvenniaTest

from commands.combat import CombatCmdSet
from combat.round_manager import CombatRoundManager, CombatInstance
from combat.combat_actions import AttackAction
from typeclasses.npcs import CombatNPC


@override_settings(DEFAULT_HOME=None)
class TestPlayerVsNPCAttack(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.char1.msg = MagicMock()
        self.char1.cmdset.add_default(CombatCmdSet)
        self.room1.msg_contents = MagicMock()

    def test_player_defeats_npc(self):
        npc = create.create_object(CombatNPC, key="mob", location=self.room1)
        npc.traits.health.current = 3
        npc.traits.health.max = 3

        manager = CombatRoundManager.get()
        manager.force_end_all_combat()

        with (
            patch.object(CombatInstance, "start"),
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
            self.assertTrue(manager.combats)
            instance = list(manager.combats.values())[0]
            while npc.hp > 0 and not instance.combat_ended:
                instance.process_round()

        self.assertTrue(mock_resolve.called)
        self.assertEqual(npc.hp, 0)
        self.assertTrue(instance.combat_ended)
