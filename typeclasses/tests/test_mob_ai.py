import unittest
from unittest.mock import patch, MagicMock

from evennia.utils import create
from evennia.utils.test_resources import EvenniaTest

from world.npc_handlers import mob_ai
from scripts.global_npc_ai import GlobalNPCAI


class TestMobAIScript(EvenniaTest):
    def test_script_calls_mob_ai(self):
        from scripts.global_npc_ai import GlobalNPCAI
        from typeclasses.npcs import BaseNPC

        npc = create.create_object(BaseNPC, key="mob", location=self.room1)
        npc.db.ai_type = "aggressive"
        npc.tags.add("npc_ai")
        script = GlobalNPCAI()

        with patch("scripts.global_npc_ai.process_mob_ai") as mock_proc:
            script.at_repeat()
            mock_proc.assert_called_with(npc)


class TestMobAIBehaviors(EvenniaTest):
    def test_scavenger_picks_up_valuable_item(self):
        from typeclasses.npcs import BaseNPC
        from typeclasses.objects import Object

        npc = create.create_object(BaseNPC, key="scav", location=self.room1)
        npc.db.actflags = ["scavenger"]
        item1 = create.create_object(Object, key="cheap", location=self.room1)
        item1.db.value = 1
        item2 = create.create_object(Object, key="rich", location=self.room1)
        item2.db.value = 5

        mob_ai.process_mob_ai(npc)
        self.assertEqual(item2.location, npc)
        self.assertEqual(item1.location, self.room1)

    def test_aggressive_attacks_player(self):
        from typeclasses.npcs import BaseNPC

        npc = create.create_object(BaseNPC, key="orc", location=self.room1)
        npc.db.actflags = ["aggressive"]
        with patch.object(npc, "enter_combat") as mock:
            mob_ai.process_mob_ai(npc)
            mock.assert_called_with(self.char1)

    def test_aggressive_flag_spawns_script_and_attacks(self):
        from typeclasses.npcs import BaseNPC

        npc = create.create_object(BaseNPC, key="flag", location=self.room1)
        npc.db.actflags = ["aggressive"]
        npc.at_object_creation()

        self.assertTrue(npc.tags.get("npc_ai"))
        script = GlobalNPCAI()

        with patch.object(npc, "enter_combat") as mock:
            script.at_repeat()
            mock.assert_called_with(self.char1)

    def test_memory_attack(self):
        from typeclasses.npcs import BaseNPC

        npc = create.create_object(BaseNPC, key="ogre", location=self.room1)
        mob_ai.remember(npc, self.char1)
        with patch.object(npc, "enter_combat") as mock:
            mob_ai.process_mob_ai(npc)
            mock.assert_called_with(self.char1)

    def test_assist_allies(self):
        from typeclasses.npcs import BaseNPC
        from combat.round_manager import CombatRoundManager

        ally = create.create_object(BaseNPC, key="ally", location=self.room1)
        ally.db.ai_type = "defensive"
        ally.db.actflags = []
        manager = CombatRoundManager.get()
        instance = manager.start_combat([ally, self.char1])

        helper = create.create_object(BaseNPC, key="helper", location=self.room1)
        helper.db.actflags = ["assist"]

        with patch.object(helper, "enter_combat") as mock:
            mob_ai.process_mob_ai(helper)
            mock.assert_called_with(self.char1)
