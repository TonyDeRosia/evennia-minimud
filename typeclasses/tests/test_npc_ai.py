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


