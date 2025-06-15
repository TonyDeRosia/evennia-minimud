from unittest.mock import patch
from evennia.utils import create
from evennia.utils.test_resources import EvenniaTest

from scripts.combat_ai import BaseCombatAI
from typeclasses.npcs import BaseNPC
from typeclasses.exits import Exit
from typeclasses.rooms import Room


class TestBaseCombatAI(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.npc = create.create_object(BaseNPC, key="mob", location=self.room1)
        self.room2 = create.create_object(Room, key="room2")
        self.room3 = create.create_object(Room, key="room3")
        self.exit_target = create.create_object(
            Exit, key="east", location=self.room1, destination=self.room2
        )
        self.exit_other = create.create_object(
            Exit, key="north", location=self.room1, destination=self.room3
        )
        self.script = self.npc.scripts.add(BaseCombatAI, key="combat_ai", autostart=False)

    def test_move_prefers_adjacent_target(self):
        self.char1.location = self.room2
        with patch("scripts.combat_ai.choice", return_value=self.exit_other), \
             patch.object(self.exit_target, "at_traverse") as mock_target, \
             patch.object(self.exit_other, "at_traverse") as mock_other:
            self.script.move()
            mock_target.assert_called_with(self.npc, self.room2)
            mock_other.assert_not_called()

    def test_skip_move_if_target_present(self):
        self.script.db.skip_move_if_target = True
        self.char1.location = self.room1
        with patch.object(self.exit_target, "at_traverse") as mock_move:
            self.script.move()
            mock_move.assert_not_called()

    def test_attack_target_uses_instance(self):
        """attack_target should queue using the instance returned by start_or_get_combat."""
        mock_engine = MagicMock()
        inst = MagicMock(engine=mock_engine)
        with patch(
            "scripts.combat_ai.start_or_get_combat", return_value=inst
        ) as mock_start, patch("scripts.combat_ai.AttackAction"):
            self.script.attack_target(self.char1)
            mock_start.assert_called_with(self.npc, self.char1)
            mock_engine.queue_action.assert_called()

