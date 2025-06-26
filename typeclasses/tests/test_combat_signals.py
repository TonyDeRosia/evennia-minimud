from unittest.mock import MagicMock, patch
from django.test import override_settings
from evennia.utils.test_resources import EvenniaTest
from combat.round_manager import CombatRoundManager, CombatInstance
from combat.events import (
    combat_started,
    round_processed,
    combatant_defeated,
    combat_ended,
)
from typeclasses.tests.test_combat_engine import KillAction


@override_settings(DEFAULT_HOME=None)
class TestCombatSignals(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.manager = CombatRoundManager.get()
        self.manager.force_end_all_combat()

    def test_signals_fire_when_combatant_dies(self):
        started = MagicMock()
        processed = MagicMock()
        defeated = MagicMock()
        ended = MagicMock()

        combat_started.connect(started)
        round_processed.connect(processed)
        combatant_defeated.connect(defeated)
        combat_ended.connect(ended)

        with patch.object(CombatInstance, "start"):
            inst = self.manager.start_combat([self.char1, self.char2])

        engine = inst.engine
        engine.queue_action(self.char1, KillAction(self.char1, self.char2))

        with (
            patch("world.system.state_manager.apply_regen"),
            patch("world.system.state_manager.check_level_up"),
            patch("combat.engine.damage_processor.delay"),
            patch("random.randint", return_value=0),
        ):
            inst.process_round()

        assert started.called
        assert processed.called
        assert defeated.called
        assert ended.called
