import unittest
from unittest.mock import patch, MagicMock
from evennia.utils.test_resources import EvenniaTest
from evennia.utils import create
from django.test import override_settings

from typeclasses.characters import NPC, PlayerCharacter
from typeclasses.rooms import Room
from world.mechanics import on_death_manager
from combat.round_manager import CombatRoundManager


@override_settings(DEFAULT_HOME=None)
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

        dummy_corpse = create.create_object("typeclasses.objects.Object", key="corpse", location=None)

        def finalize_side(v, c):
            c.db.corpse_of = v.key

        with (
            patch.object(inst.engine, "award_experience") as mock_award,
            patch("world.mechanics.corpse_manager.create_corpse", return_value=dummy_corpse),
            patch("world.mechanics.corpse_manager.apply_loot"),
            patch("world.mechanics.corpse_manager.finalize_corpse", side_effect=finalize_side),
        ):
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
        inst = manager.start_combat([self.char1, npc])

        dummy_corpse = create.create_object("typeclasses.objects.Object", key="corpse", location=None)

        def finalize_side(v, c):
            c.db.corpse_of = v.key

        with (
            patch("world.system.state_manager.gain_xp") as mock_gain,
            patch.object(inst.engine, "award_experience") as mock_award,
            patch("world.mechanics.corpse_manager.create_corpse", return_value=dummy_corpse),
            patch("world.mechanics.corpse_manager.apply_loot"),
            patch("world.mechanics.corpse_manager.finalize_corpse", side_effect=finalize_side),
        ):
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

        def create_corpse_side(victim):
            order.append("corpse")
            corpse = create.create_object("typeclasses.objects.Object", key="corpse", location=None)
            return corpse

        def apply_loot_side(victim, corpse, killer=None):
            order.append("loot")
            loot = MagicMock(key="loot")
            loot.location = corpse
            corpse.contents.append(loot)

        npc.msg = MagicMock(side_effect=record_msg)
        self.room.msg_contents = MagicMock(side_effect=record_msg)

        with (
            patch("world.mechanics.corpse_manager.create_corpse", side_effect=create_corpse_side),
            patch("world.mechanics.corpse_manager.apply_loot", side_effect=apply_loot_side),
            patch("world.mechanics.corpse_manager.finalize_corpse"),
        ):
            corpse = on_death_manager.handle_death(npc, self.char1)

        self.assertEqual(order[0], "msg")
        self.assertEqual(order[1], "msg")
        self.assertEqual(order[2], "corpse")
        self.assertEqual(order[3], "loot")
        self.assertIs(corpse.location, self.room)


if __name__ == "__main__":
    unittest.main()
