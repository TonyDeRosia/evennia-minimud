from unittest.mock import MagicMock
from django.test import override_settings
from evennia.utils import create
from evennia.utils.test_resources import EvenniaTest
from typeclasses.npcs import BaseNPC


@override_settings(DEFAULT_HOME=None)
class TestLookCommand(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.char1.msg = MagicMock()

    def test_numbered_targets(self):
        slime1 = create.create_object(BaseNPC, key="slime", location=self.room1)
        slime2 = create.create_object(BaseNPC, key="slime", location=self.room1)
        slime1.db.desc = "first slime"
        slime2.db.desc = "second slime"

        self.char1.execute_cmd("look slime")
        self.char1.msg.assert_any_call(slime1.return_appearance(self.char1))

        self.char1.msg.reset_mock()

        self.char1.execute_cmd("look slime-2")
        self.char1.msg.assert_any_call(slime2.return_appearance(self.char1))

    def test_dead_npc_hidden_in_room_contents(self):
        from typeclasses.objects import Corpse

        npc = create.create_object(BaseNPC, key="orc", location=self.room1)
        corpse = create.create_object(Corpse, key="orc corpse", location=self.room1)
        corpse.db.corpse_of = npc.key
        npc.db.is_dead = True

        self.char1.execute_cmd("look")
        output = " ".join(
            str(arg) for call in self.char1.msg.call_args_list for arg in call.args
        )
        self.assertIn(corpse.get_display_name(self.char1), output)
        self.assertNotIn(npc.get_display_name(self.char1), output)
