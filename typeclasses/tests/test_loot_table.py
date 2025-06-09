from unittest.mock import patch, MagicMock
from evennia.utils import create
from evennia.utils.test_resources import EvenniaTest

class TestNPCLootTable(EvenniaTest):
    def test_loot_table_spawn(self):
        from typeclasses.characters import NPC

        npc = create.create_object(NPC, key="mob", location=self.room1)
        npc.db.drops = []
        npc.db.loot_table = [{"proto": "RAW_MEAT", "chance": 100}]
        npc.traits.health.current = 1
        with patch("evennia.prototypes.spawner.spawn", return_value=[MagicMock()]) as mock_spawn:
            npc.at_damage(self.char1, 2)
            mock_spawn.assert_called_with("RAW_MEAT")

