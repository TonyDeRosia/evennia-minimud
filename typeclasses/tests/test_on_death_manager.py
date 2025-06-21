import unittest
from unittest.mock import patch, MagicMock
from evennia.utils.test_resources import EvenniaTest
from evennia.utils import create

from typeclasses.characters import NPC, PlayerCharacter
from typeclasses.rooms import Room
from world.mechanics import on_death_manager
from combat.round_manager import CombatRoundManager


class TestOnDeathManager(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.room = create.create_object(Room, key="room")
        self.char1.location = self.room
        self.char1.msg = MagicMock()

    def test_npc_death_awards_xp_and_leaves_combat(self):
        npc = create.create_object(NPC, key="mob", location=self.room)
        npc.db.drops = []
        npc.db.exp_reward = 5
        manager = CombatRoundManager.get()
        manager.force_end_all_combat()
        inst = manager.start_combat([self.char1, npc])

        with patch.object(inst.engine, "award_experience") as mock_award:
            on_death_manager.handle_death(npc, self.char1)

        mock_award.assert_called_once_with(self.char1, npc)
        self.assertIsNone(manager.get_combatant_combat(npc))
        corpse = next(obj for obj in self.room.contents if obj.db.corpse_of == npc.key)
        self.assertIsNotNone(corpse)

    def test_player_death_creates_corpse_and_clears_combat(self):
        npc = create.create_object(NPC, key="mob", location=self.room)
        npc.db.drops = []
        manager = CombatRoundManager.get()
        manager.force_end_all_combat()
        manager.start_combat([self.char1, npc])

        with patch("world.system.state_manager.gain_xp") as mock_gain:
            on_death_manager.handle_death(self.char1, npc)

        mock_gain.assert_not_called()
        self.assertIsNone(manager.get_combatant_combat(self.char1))
        corpse = next(obj for obj in self.room.contents if obj.db.corpse_of == self.char1.key)
        self.assertIsNotNone(corpse)

    def test_death_message_then_corpse_loot(self):
        npc = create.create_object(NPC, key="mob", location=self.room)
        npc.db.drops = []
        order = []

        def record_msg(*args, **kwargs):
            order.append("msg")

        def drop_loot_side(killer=None):
            order.append("corpse")
            corpse = create.create_object("typeclasses.objects.Corpse", key="corpse", location=None)
            loot = create.create_object("typeclasses.objects.Object", key="loot", location=corpse)
            return corpse

        npc.msg = MagicMock(side_effect=record_msg)
        self.room.msg_contents = MagicMock(side_effect=record_msg)
        npc.drop_loot = MagicMock(side_effect=drop_loot_side)

        on_death_manager.handle_death(npc, self.char1)

        self.assertEqual(order[0], "msg")
        self.assertEqual(order[1], "msg")
        self.assertEqual(order[2], "corpse")


if __name__ == "__main__":
    unittest.main()
