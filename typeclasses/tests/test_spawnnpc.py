from unittest.mock import MagicMock
from evennia.utils.test_resources import EvenniaTest
from commands.admin import BuilderCmdSet
from typeclasses.npcs import MerchantNPC


class TestSpawnNPCPrototype(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.char1.msg = MagicMock()
        self.char1.cmdset.add_default(BuilderCmdSet)

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
