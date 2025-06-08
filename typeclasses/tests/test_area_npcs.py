from unittest.mock import MagicMock
from evennia.utils.test_resources import EvenniaTest
from django.test import override_settings
from commands.admin import BuilderCmdSet
from world import area_npcs, prototypes

@override_settings(DEFAULT_HOME=None)
class TestAreaNPCRegistry(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.char1.msg = MagicMock()
        self.char1.cmdset.add_default(BuilderCmdSet)
        area_npcs.remove_area_npc("testarea", "basic_merchant")

    def test_add_and_remove(self):
        area_npcs.add_area_npc("testarea", "basic_merchant")
        self.assertIn("basic_merchant", area_npcs.get_area_npc_list("testarea"))
        area_npcs.remove_area_npc("testarea", "basic_merchant")
        self.assertNotIn("basic_merchant", area_npcs.get_area_npc_list("testarea"))

    def test_commands(self):
        area_npcs.add_area_npc("testarea", "basic_merchant")
        # listnpcs
        self.char1.execute_cmd("@listnpcs testarea")
        out = self.char1.msg.call_args[0][0]
        self.assertIn("basic_merchant", out)
        # spawnnpc
        self.char1.msg.reset_mock()
        self.char1.execute_cmd("@spawnnpc testarea/basic_merchant")
        objs = [o for o in self.char1.location.contents if o.key == "merchant"]
        self.assertTrue(objs)
        # dupnpc
        self.char1.msg.reset_mock()
        self.char1.execute_cmd("@dupnpc testarea/basic_merchant = special_merchant")
        reg = prototypes.get_npc_prototypes()
        self.assertIn("special_merchant", reg)
        self.assertIn("special_merchant", area_npcs.get_area_npc_list("testarea"))
