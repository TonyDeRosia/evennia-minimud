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
            room = npc.location
            npc.at_damage(self.char1, 2)
            mock_spawn.assert_called_with("RAW_MEAT")

            corpse = next(
                obj
                for obj in room.contents
                if obj.is_typeclass("typeclasses.objects.Corpse", exact=False)
            )
            item = mock_spawn.return_value[0]
            self.assertIs(item.location, corpse)

    def test_loot_table_guaranteed_after(self):
        from typeclasses.characters import NPC

        npc = create.create_object(NPC, key="mob", location=self.room1)
        npc.db.drops = []
        npc.db.loot_table = [{"proto": "RAW_MEAT", "chance": 0, "guaranteed_after": 2}]
        npc.traits.health.current = 1
        with patch("evennia.prototypes.spawner.spawn", return_value=[MagicMock()]) as mock_spawn, \
             patch("typeclasses.characters.randint", return_value=100), \
             patch.object(npc, "delete"):
            npc.at_damage(self.char1, 2)  # first kill, no drop
            npc.traits.health.current = 1
            npc.at_damage(self.char1, 2)  # second kill, still no drop
            npc.traits.health.current = 1
            npc.at_damage(self.char1, 2)  # third kill, guaranteed drop
            mock_spawn.assert_called_with("RAW_MEAT")

            item = mock_spawn.return_value[0]
            self.assertTrue(
                item.location.is_typeclass("typeclasses.objects.Corpse", exact=False)
            )

