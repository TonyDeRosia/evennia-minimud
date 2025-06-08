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


