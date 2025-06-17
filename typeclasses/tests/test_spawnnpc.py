from unittest.mock import MagicMock, patch
from evennia.utils.test_resources import EvenniaTest
from commands.admin import BuilderCmdSet
from tempfile import TemporaryDirectory
from pathlib import Path
from django.conf import settings
from unittest import mock
from typeclasses.npcs import MerchantNPC, BaseNPC
from evennia.contrib.rpg.traits import TraitHandler
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
        self.assertIsInstance(npc.traits, TraitHandler)

    def test_spawn_basic_questgiver_has_traits(self):
        self.char1.execute_cmd("@spawnnpc basic_questgiver")
        npc = self._find("quest giver")
        self.assertIsNotNone(npc)
        self.assertIsInstance(npc.traits, TraitHandler)

    def test_spawn_basic_guard_has_traits(self):
        self.char1.execute_cmd("@spawnnpc basic_guard")
        npc = self._find("town guard")
        self.assertIsNotNone(npc)
        self.assertIsInstance(npc.traits, TraitHandler)


    def test_old_prototype_fallback(self):
        from world import prototypes

        prototypes.register_npc_prototype(
            "legacy_proto",
            {"key": "legacy", "npc_type": "merchant"},
        )

        self.char1.execute_cmd("@spawnnpc legacy_proto")
        npc = self._find("legacy")
        self.assertIsNotNone(npc)
        self.assertTrue(npc.tags.has("merchant", category="npc_type"))

    def test_vnum_not_finalized_message(self):
        """Numeric VNUMs without prototypes should show a specific error."""
        with patch("utils.mob_proto.spawn_from_vnum") as mock_spawn:
            self.char1.execute_cmd("@spawnnpc 42")
            mock_spawn.assert_not_called()
        out = self.char1.msg.call_args[0][0]
        self.assertIn("Invalid VNUM", out)
        self.assertIn("never finalized", out)


