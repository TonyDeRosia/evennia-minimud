from unittest.mock import MagicMock, patch
from evennia.utils.test_resources import EvenniaTest
from django.test import override_settings
from commands.admin import BuilderCmdSet
from commands import npc_builder
from evennia.utils import create


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
        npc_builder._set_creature_type(self.char1, "humanoid")
        npc_builder._set_npc_type(self.char1, "merchant")
        npc_builder._edit_roles(self.char1, "add merchant")
        npc_builder._edit_roles(self.char1, "done")
        npc_builder._set_merchant_pricing(self.char1, "1.5")
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
        self.assertTrue(npc.tags.has("merchant", category="npc_type"))
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
        self.assertEqual(npc.db.equipment_slots, list(npc_builder.SLOT_ORDER))
        self.assertEqual(npc.db.merchant_markup, 1.5)
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
        npc_builder._set_creature_type(self.char1, "humanoid")
        npc_builder._set_npc_type(self.char1, "guard")
        npc_builder._set_level(self.char1, "1")
        npc_builder._set_resources(self.char1, "20 5 5")
        npc_builder._set_stats(self.char1, "5 5 5 5 5 5")
        npc_builder._set_behavior(self.char1, "dumb")
        npc_builder._set_skills(self.char1, "smash")
        npc_builder._set_ai(self.char1, "defensive")
        npc_builder._create_npc(self.char1, "", register=True)

        from world.prototypes import get_npc_prototypes

        registry = get_npc_prototypes()
        self.assertIn("ogre", registry)
        self.assertEqual(registry["ogre"]["desc"], "A big ogre")

    def test_triggers_and_reactions(self):
        with patch("commands.npc_builder.EvMenu"):
            self.char1.execute_cmd("cnpc start parrot")

        npc_builder._set_desc(self.char1, "A colorful parrot")
        npc_builder._set_creature_type(self.char1, "humanoid")
        npc_builder._set_npc_type(self.char1, "craftsman")
        npc_builder._set_level(self.char1, "1")
        npc_builder._set_resources(self.char1, "10 0 0")
        npc_builder._set_stats(self.char1, "1 1 1 1 1 1")
        npc_builder._set_behavior(self.char1, "chatty")
        npc_builder._set_skills(self.char1, "")
        npc_builder._set_ai(self.char1, "passive")

        self.char1.ndb.buildnpc["triggers"] = {
            "on_speak": ("hello", "say Squawk!"),
            "on_give_item": ("", "say Thanks!"),
        }

        npc_builder._create_npc(self.char1, "")

        npc = self._find("parrot")
        self.assertIsNotNone(npc)
        self.assertEqual(
            npc.db.triggers,
            {
                "on_speak": ("hello", "say Squawk!"),
                "on_give_item": ("", "say Thanks!"),
            },
        )

        with patch.object(npc, "execute_cmd") as mock_exec:
            npc.at_say(self.char2, "hello there")
        with patch.object(npc, "execute_cmd") as mock_exec:
            npc.at_object_receive(self.obj1, self.char2)

    def test_unique_slots(self):
        with patch("commands.npc_builder.EvMenu"):
            self.char1.execute_cmd("cnpc start chimera")

        npc_builder._set_desc(self.char1, "A weird beast")
        npc_builder._set_creature_type(self.char1, "unique")
        npc_builder._edit_custom_slots(self.char1, "remove offhand")
        npc_builder._edit_custom_slots(self.char1, "add tail")
        npc_builder._edit_custom_slots(self.char1, "done")
        npc_builder._set_npc_type(self.char1, "guard")
        npc_builder._set_level(self.char1, "1")
        npc_builder._set_resources(self.char1, "5 0 0")
        npc_builder._set_stats(self.char1, "1 1 1 1 1 1")
        npc_builder._set_behavior(self.char1, "")
        npc_builder._set_skills(self.char1, "")
        npc_builder._set_ai(self.char1, "passive")
        npc_builder._create_npc(self.char1, "")

        npc = self._find("chimera")
        self.assertIn("tail", npc.db.equipment_slots)
        self.assertNotIn("offhand", npc.db.equipment_slots)

    def test_role_details(self):
        with patch("commands.npc_builder.EvMenu"):
            self.char1.execute_cmd("cnpc start clerk")

        npc_builder._set_desc(self.char1, "A helpful clerk")
        npc_builder._set_creature_type(self.char1, "humanoid")
        npc_builder._set_npc_type(self.char1, "wanderer")
        npc_builder._edit_roles(self.char1, "add guild_receptionist")
        npc_builder._edit_roles(self.char1, "done")
        npc_builder._set_guild_affiliation(self.char1, "myguild")
        npc_builder._set_level(self.char1, "1")
        npc_builder._set_resources(self.char1, "5 0 0")
        npc_builder._set_stats(self.char1, "1 1 1 1 1 1")
        npc_builder._set_behavior(self.char1, "")
        npc_builder._set_skills(self.char1, "")
        npc_builder._set_ai(self.char1, "scripted")
        npc_builder._create_npc(self.char1, "")

        npc = self._find("clerk")
        self.assertTrue(npc.tags.has("myguild", category="guild_affiliation"))
        self.assertTrue(npc.tags.has("guild_receptionist", category="npc_role"))
        self.assertEqual(npc.db.ai_type, "scripted")

    def test_confirm_incomplete_data(self):
        """menunode_confirm should handle missing data gracefully."""
        self.char1.ndb.buildnpc = {}
        result = npc_builder.menunode_confirm(self.char1)
        self.assertIsNone(result)
        self.char1.msg.assert_called()
        msg = self.char1.msg.call_args[0][0]
        self.assertIn("Error", msg)
