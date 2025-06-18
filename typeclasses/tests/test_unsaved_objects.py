import unittest
from unittest.mock import MagicMock, patch

from evennia.utils.test_resources import EvenniaTest
from typeclasses.characters import Character, NPC
from combat.round_manager import CombatRoundManager, CombatInstance
from combat.engine import CombatEngine
from combat.combat_states import CombatStateManager, CombatState


class TestUnsavedEvenniaObjects(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.manager = CombatRoundManager.get()
        self.manager.combats.clear()
        self.manager.combatant_to_combat.clear()

    def make_unsaved(self, cls):
        obj = cls(db_key="temp")
        obj.pk = None
        obj.save = MagicMock()
        obj.location = MagicMock()
        obj.traits = MagicMock()
        obj.traits.get.return_value = MagicMock(value=0)
        obj.traits.health = MagicMock(value=10, max=10)
        obj.on_enter_combat = MagicMock()
        obj.on_exit_combat = MagicMock()
        obj.msg = MagicMock()
        return obj

    def test_create_combat_with_unsaved_objects(self):
        char = self.make_unsaved(Character)
        npc = self.make_unsaved(NPC)
        with patch.object(CombatInstance, "start"):
            inst = self.manager.create_combat([char, npc])
        self.assertIn(char, inst.combatants)
        self.assertIn(npc, inst.combatants)

    def test_start_combat_with_unsaved_objects(self):
        char = self.make_unsaved(Character)
        npc = self.make_unsaved(NPC)
        with patch.object(CombatInstance, "start"):
            inst = self.manager.start_combat([char, npc])
        self.assertIn(char, inst.combatants)
        self.assertIn(npc, inst.combatants)

    def test_state_manager_accepts_unsaved(self):
        char = self.make_unsaved(Character)
        manager = CombatStateManager()
        state = CombatState(key="bleeding", duration=1)
        manager.add_state(char, state)
        self.assertIn(char, manager.states)
        self.assertIn("bleeding", manager.states[char])
