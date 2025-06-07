from unittest.mock import MagicMock, patch
from evennia.utils.test_resources import EvenniaTest
from django.test import override_settings
from commands.admin import BuilderCmdSet
from commands import npc_builder


@override_settings(DEFAULT_HOME=None)
class TestCNPC(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.char1.msg = MagicMock()
        self.char2.msg = MagicMock()
        self.char1.cmdset.add_default(BuilderCmdSet)
        self.char2.cmdset.add_default(BuilderCmdSet)

    def _find(self, key, location=None):
        location = location or self.char1.location
        for obj in location.contents:
            if obj.key == key:
                return obj
        return None

    def test_cnpc_workflow(self):
        with patch("commands.npc_builder.EvMenu"):
            self.char1.execute_cmd("cnpc start goblin")

        npc_builder._set_desc(self.char1, "A nasty goblin")
        npc_builder._set_npc_type(self.char1, "monster")
        npc_builder._set_creature_type(self.char1, "humanoid")
        npc_builder._set_level(self.char1, "2")
        npc_builder._set_resources(self.char1, "30 10 5")
        npc_builder._set_stats(self.char1, "5 4 6 3 2 1")
        npc_builder._set_behavior(self.char1, "aggressive")
        npc_builder._set_skills(self.char1, "slash, stab")
        npc_builder._set_ai(self.char1, "aggressive")
        npc_builder._create_npc(self.char1, "")

        npc = self._find("goblin")
        self.assertIsNotNone(npc)
        self.assertTrue(npc.tags.has("npc"))
        self.assertTrue(npc.tags.has("monster", category="npc_type"))
        self.assertEqual(npc.db.base_primary_stats, {
            "STR": 5,
            "CON": 4,
            "DEX": 6,
            "INT": 3,
            "WIS": 2,
            "LUCK": 1,
        })
        self.assertEqual(npc.traits.health.base, 30)
        self.assertEqual(npc.traits.mana.base, 10)
        self.assertEqual(npc.traits.stamina.base, 5)
        self.assertEqual(npc.location, self.char1.location)
        self.assertIsNone(self.char1.ndb.buildnpc)

    def test_builder_lock(self):
        with patch("commands.npc_builder.EvMenu"):
            self.char2.execute_cmd("cnpc start thief")
        self.assertIsNone(getattr(self.char2.ndb, "buildnpc", None))
        self.assertIsNone(self._find("thief", location=self.char2.location))

    def test_prototype_registration(self):
        with patch("commands.npc_builder.EvMenu"):
            self.char1.execute_cmd("cnpc start ogre")

        npc_builder._set_desc(self.char1, "A big ogre")
        npc_builder._set_npc_type(self.char1, "monster")
        npc_builder._set_creature_type(self.char1, "humanoid")
        npc_builder._set_level(self.char1, "1")
        npc_builder._set_resources(self.char1, "20 5 5")
        npc_builder._set_stats(self.char1, "5 5 5 5 5 5")
        npc_builder._set_behavior(self.char1, "dumb")
        npc_builder._set_skills(self.char1, "smash")
        npc_builder._set_ai(self.char1, "passive")
        npc_builder._create_npc(self.char1, "", register=True)

        from world.prototypes import get_npc_prototypes

        registry = get_npc_prototypes()
        self.assertIn("ogre", registry)
        self.assertEqual(registry["ogre"]["desc"], "A big ogre")
