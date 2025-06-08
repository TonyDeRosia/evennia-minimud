from unittest.mock import patch

from evennia.utils import create
from evennia.utils.test_resources import EvenniaTest


class TestNPCAIScript(EvenniaTest):
    def test_script_calls_process_ai(self):
        from scripts.npc_ai_script import NPCAIScript
        from typeclasses.npcs import BaseNPC

        npc = create.create_object(BaseNPC, key="mob", location=self.room1)
        npc.db.ai_type = "aggressive"
        npc.scripts.add(NPCAIScript, key="npc_ai", autostart=False)
        script = npc.scripts.get("npc_ai")[0]

        with patch("scripts.npc_ai_script.process_ai") as mock_proc:
            script.at_repeat()
            mock_proc.assert_called_with(npc)

    def test_base_npc_spawns_ai_script(self):
        from typeclasses.npcs import BaseNPC

        npc = create.create_object(BaseNPC, key="mob2", location=self.room1)
        npc.db.ai_type = "passive"
        npc.at_object_creation()
        self.assertTrue(npc.scripts.get("npc_ai"))

    def test_scripted_ai_string_callback(self):
        from world.npc_handlers import ai
        from typeclasses.npcs import BaseNPC

        npc = create.create_object(BaseNPC, key="mob3", location=self.room1)
        npc.db.ai_type = "scripted"
        npc.db.ai_script = "scripts.example_ai.patrol_ai"

        with patch("scripts.example_ai.patrol_ai") as mock_call:
            ai.process_ai(npc)
            mock_call.assert_called_with(npc)

    def test_scripted_ai_direct_callable(self):
        from world.npc_handlers import ai
        from typeclasses.npcs import BaseNPC

        called = {}

        def callback(obj):
            called["ran"] = obj

        npc = create.create_object(BaseNPC, key="mob4", location=self.room1)
        npc.db.ai_type = "scripted"
        npc.db.ai_script = callback

        ai.process_ai(npc)
        self.assertIs(called.get("ran"), npc)

    def test_wanderer_defaults_to_wander_ai(self):
        from typeclasses.npcs import WandererNPC

        npc = create.create_object(WandererNPC, key="wander", location=self.room1)
        npc.at_object_creation()

        self.assertEqual(npc.db.ai_type, "wander")
        self.assertTrue(npc.scripts.get("npc_ai"))



class TestAIBehaviors(EvenniaTest):
    def test_aggressive_ai_enters_combat(self):
        from world.npc_handlers import ai
        from typeclasses.npcs import BaseNPC

        npc = create.create_object(BaseNPC, key="agg", location=self.room1)
        npc.db.ai_type = "aggressive"
        with patch.object(npc, "enter_combat") as mock:
            ai.process_ai(npc)
            mock.assert_called()

    def test_defensive_ai_attacks_only_in_combat(self):
        from world.npc_handlers import ai
        from typeclasses.npcs import BaseNPC

        npc = create.create_object(BaseNPC, key="def", location=self.room1)
        npc.db.ai_type = "defensive"
        npc.in_combat = False
        with patch.object(npc, "attack") as mock:
            ai.process_ai(npc)
            mock.assert_not_called()
        npc.in_combat = True
        npc.db.combat_target = self.char1
        with patch.object(npc, "attack") as mock:
            ai.process_ai(npc)
            mock.assert_called_with(self.char1, npc)

    def test_wander_ai_moves(self):
        from world.npc_handlers import ai
        from typeclasses.npcs import BaseNPC
        from typeclasses.exits import Exit

        dest = create.create_object("typeclasses.rooms.Room", key="dest")
        exit_obj = create.create_object(Exit, key="east", location=self.room1)
        exit_obj.destination = dest
        npc = create.create_object(BaseNPC, key="wander", location=self.room1)
        npc.db.ai_type = "wander"
        with patch.object(exit_obj, "at_traverse") as mock:
            ai.process_ai(npc)
            mock.assert_called_with(npc, dest)

    def test_invalid_ai_type_no_action(self):
        from world.npc_handlers import ai
        from typeclasses.npcs import BaseNPC

        npc = create.create_object(BaseNPC, key="none", location=self.room1)
        npc.db.ai_type = "bogus"
        with patch.object(npc, "attack") as mock:
            ai.process_ai(npc)
            mock.assert_not_called()
