from unittest.mock import MagicMock
from evennia.utils.test_resources import EvenniaTest
from commands.admin import BuilderCmdSet
from unittest.mock import patch
from typeclasses.npcs import MerchantNPC, BaseNPC
from scripts.area_spawner import AreaSpawner
from world import area_npcs


class TestSpawnNPCPrototype(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.char1.msg = MagicMock()
        self.char1.cmdset.add_default(BuilderCmdSet)
        self.char1.location.db.area = "testarea"

    def _find(self, key):
        for obj in self.char1.location.contents:
            if obj.key == key:
                return obj
        return None

    def test_spawn_basic_merchant(self):
        self.char1.execute_cmd("@spawnnpc basic_merchant")
        npc = self._find("merchant")
        self.assertIsNotNone(npc)
        self.assertTrue(npc.is_typeclass(MerchantNPC, exact=False))
        self.assertTrue(npc.tags.has("merchant", category="npc_type"))
        self.assertEqual(npc.db.ai_type, "passive")
        self.assertEqual(npc.db.prototype_key, "basic_merchant")
        self.assertIs(npc.db.spawn_room, self.char1.location)
        self.assertEqual(npc.db.area_tag, "testarea")

    @patch("scripts.area_spawner.choice", return_value="basic_merchant")
    @patch("scripts.area_spawner.randint", return_value=1)
    def test_area_spawner_sets_attributes(self, mock_randint, mock_choice):
        area_npcs.add_area_npc("testarea", "basic_merchant")
        script = self.char1.location.scripts.add(
            AreaSpawner, key="area_spawner", autostart=False
        )
        script.db.spawn_chance = 100
        script.at_repeat()
        npc = [o for o in self.char1.location.contents if o.is_typeclass(BaseNPC, exact=False)][0]
        self.assertEqual(npc.db.prototype_key, "basic_merchant")
        self.assertIs(npc.db.spawn_room, self.char1.location)
        self.assertEqual(npc.db.area_tag, "testarea")
