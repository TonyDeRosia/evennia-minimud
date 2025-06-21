import unittest
from unittest.mock import patch, MagicMock

from combat.round_manager import CombatRoundManager, CombatInstance
from combat.engine import CombatEngine
from combat.combat_actions import Action, CombatResult

class Dummy:
    def __init__(self, hp=10):
        self.hp = hp
        self.location = MagicMock()
        self.location.contents = []
        self.traits = MagicMock()
        self.traits.get.return_value = MagicMock(value=0)
        self.traits.health = MagicMock(current=hp, value=hp, max=hp)
        self.db = type('DB', (), {'temp_bonuses': {}, 'experience': 0, 'tnl': 0, 'level': 1, 'combat_target': None})()
        self.on_enter_combat = MagicMock()
        self.on_exit_combat = MagicMock()
        self.msg = MagicMock()

class KillAction(Action):
    def resolve(self):
        self.target.hp = 0
        if hasattr(self.target.traits, 'health'):
            self.target.traits.health.current = 0
        return CombatResult(self.actor, self.target, 'boom')

class TestActiveFighterTracking(unittest.TestCase):
    def setUp(self):
        self.manager = CombatRoundManager.get()
        self.manager.combats.clear()
        self.manager.combatant_to_combat.clear()

    def test_removed_participant_keeps_combat_alive(self):
        player = Dummy()
        npc = Dummy()
        with patch.object(CombatInstance, '_schedule_tick'), \
             patch.object(CombatEngine, 'process_round'):
            inst = self.manager.create_combat([player, npc])
            # remove npc from engine participants without removing from combatants
            inst.engine.remove_participant(npc)
            # ensure still considered active
            self.assertTrue(inst.has_active_fighters())
            inst._tick()
        self.assertFalse(inst.combat_ended)


class TestDefeatRewards(unittest.TestCase):
    def setUp(self):
        self.manager = CombatRoundManager.get()
        self.manager.combats.clear()
        self.manager.combatant_to_combat.clear()

    def test_defeat_creates_corpse_and_awards_xp(self):
        attacker = Dummy()
        defender = Dummy()
        loc = MagicMock()
        attacker.location = defender.location = loc
        engine = CombatEngine([attacker, defender], round_time=0)
        inst = CombatInstance(1, engine, {attacker, defender})
        self.manager.combats[1] = inst
        with patch('combat.damage_processor.spawn_corpse') as mock_corpse, \
             patch.object(CombatEngine, 'award_experience') as mock_xp:
            engine.processor.handle_defeat(defender, attacker)
            mock_corpse.assert_called()
            mock_xp.assert_called_with(attacker, defender)

