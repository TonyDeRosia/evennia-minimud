import unittest
from unittest.mock import MagicMock, patch

from combat.engine import CombatEngine
from combat.combat_actions import AttackAction
from combat.damage_types import DamageType


class Dummy:
    def __init__(self, hp=10):
        self.hp = hp
        self.key = "dummy"
        self.location = MagicMock()
        self.traits = MagicMock()
        self.traits.get.return_value = MagicMock(value=0)
        self.traits.health = MagicMock(value=hp, max=hp)
        self.traits.mana = MagicMock(current=20)
        self.traits.stamina = MagicMock(current=20)
        self.cooldowns = MagicMock()
        self.cooldowns.ready.return_value = True
        self.tags = MagicMock()
        self.wielding = []
        self.db = type(
            "DB",
            (),
            {
                "temp_bonuses": {},
                "status_effects": {},
                "active_effects": {},
                "get": lambda *a, **k: 0,
            },
        )()
        self.attack = MagicMock()
        self.on_enter_combat = MagicMock()
        self.on_exit_combat = MagicMock()
        self.cast_spell = MagicMock()
        self.use_skill = MagicMock()


class TestAttackReactions(unittest.TestCase):
    def setUp(self):
        self.attacker = Dummy()
        self.defender = Dummy()
        weapon = MagicMock()
        weapon.damage = 5
        weapon.damage_type = DamageType.SLASHING
        weapon.at_attack = MagicMock()
        self.attacker.wielding = [weapon]
        self.attacker.location = self.defender.location

    def _run_engine(self):
        engine = CombatEngine([self.attacker, self.defender], round_time=0)
        engine.queue_action(self.attacker, AttackAction(self.attacker, self.defender))
        engine.start_round()
        engine.process_round()

    def test_attack_parried(self):
        with patch("combat.combat_actions.utils.inherits_from", return_value=True), \
             patch("world.system.state_manager.apply_regen"), \
             patch("world.system.state_manager.get_effective_stat", return_value=0), \
             patch("world.system.stat_manager.check_hit", return_value=True), \
             patch("combat.combat_utils.roll_evade", return_value=False), \
             patch("combat.combat_utils.roll_parry", return_value=True) as mock_parry, \
             patch("combat.combat_utils.roll_block", return_value=False), \
             patch("world.system.stat_manager.roll_crit", return_value=False):
            self._run_engine()
        self.assertEqual(self.defender.hp, 10)
        calls = [c.args[0] for c in self.attacker.location.msg_contents.call_args_list]
        self.assertTrue(any("parries" in msg for msg in calls))
        mock_parry.assert_called()

    def test_attack_blocked(self):
        with patch("combat.combat_actions.utils.inherits_from", return_value=True), \
             patch("world.system.state_manager.apply_regen"), \
             patch("world.system.state_manager.get_effective_stat", return_value=0), \
             patch("world.system.stat_manager.check_hit", return_value=True), \
             patch("combat.combat_utils.roll_evade", return_value=False), \
             patch("combat.combat_utils.roll_parry", return_value=False) as mp, \
             patch("combat.combat_utils.roll_block", return_value=True) as mb, \
             patch("world.system.stat_manager.roll_crit", return_value=False):
            self._run_engine()
        self.assertEqual(self.defender.hp, 10)
        calls = [c.args[0] for c in self.attacker.location.msg_contents.call_args_list]
        self.assertTrue(any("blocks" in msg for msg in calls))
        mp.assert_called()
        mb.assert_called()

    def test_attack_critical(self):
        with patch("combat.combat_actions.utils.inherits_from", return_value=True), \
             patch("world.system.state_manager.apply_regen"), \
             patch("world.system.state_manager.get_effective_stat", return_value=0), \
             patch("world.system.stat_manager.check_hit", return_value=True), \
             patch("combat.combat_utils.roll_evade", return_value=False), \
             patch("combat.combat_utils.roll_parry", return_value=False) as mp, \
             patch("combat.combat_utils.roll_block", return_value=False) as mb, \
             patch("world.system.stat_manager.roll_crit", return_value=True) as mcrit, \
             patch("world.system.stat_manager.crit_damage", return_value=10) as mcd:
            self._run_engine()
        self.assertEqual(self.defender.hp, 0)
        calls = [c.args[0] for c in self.attacker.location.msg_contents.call_args_list]
        self.assertTrue(any("Critical" in msg for msg in calls))
        mp.assert_called()
        mb.assert_called()
        mcrit.assert_called()
        mcd.assert_called_with(self.attacker, 5)
