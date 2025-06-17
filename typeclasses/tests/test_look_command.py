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
