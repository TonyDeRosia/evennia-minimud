from unittest.mock import patch, MagicMock
from evennia.utils import create
from evennia.utils.test_resources import EvenniaTest
from utils.currency import from_copper, to_copper

class TestNPCLootTable(EvenniaTest):
    def test_loot_table_spawn(self):
        from typeclasses.characters import NPC

        npc = create.create_object(NPC, key="mob", location=self.room1)
        npc.db.drops = []
        npc.db.loot_table = [{"proto": 100001, "chance": 100}]
        npc.db.coin_drop = {"gold": 1}
        self.char1.db.coins = from_copper(0)
        npc.traits.health.current = 1
        proto_data = {"key": "ruby dagger"}
        with patch("utils.prototype_manager.load_prototype", return_value=proto_data) as load_mock, \
             patch("evennia.prototypes.spawner.spawn", return_value=[MagicMock()]) as mock_spawn:
            room = npc.location
            npc.at_damage(self.char1, 2)
            load_mock.assert_called_with("object", 100001)
            mock_spawn.assert_called_with(proto_data)

            corpse = next(
                obj
                for obj in room.contents
                if obj.is_typeclass("typeclasses.objects.Corpse", exact=False)
            )
            item = mock_spawn.return_value[0]
            self.assertIs(item.location, corpse)
            self.assertEqual(to_copper(self.char1.db.coins), to_copper({"gold": 1}))

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

    def test_loot_table_coin_amount(self):
        from typeclasses.characters import NPC

        npc = create.create_object(NPC, key="mob", location=self.room1)
        npc.db.drops = []
        npc.db.loot_table = [{"proto": "gold", "chance": 100, "amount": 5}]
        npc.traits.health.current = 1
        self.char1.db.coins = from_copper(0)
        with patch("evennia.prototypes.spawner.spawn", return_value=[]):
            npc.at_damage(self.char1, 2)
        self.assertEqual(to_copper(self.char1.db.coins), to_copper({"gold": 5}))

    def test_loot_table_coin_dice_amount(self):
        from typeclasses.characters import NPC

        npc = create.create_object(NPC, key="mob", location=self.room1)
        npc.db.drops = []
        npc.db.loot_table = [{"proto": "gold", "chance": 100, "amount": "2d6"}]
        npc.traits.health.current = 1
        self.char1.db.coins = from_copper(0)
        with patch("evennia.prototypes.spawner.spawn", return_value=[]), \
             patch("utils.dice.roll_dice_string", return_value=7):
            npc.at_damage(self.char1, 2)
        self.assertEqual(to_copper(self.char1.db.coins), to_copper({"gold": 7}))

