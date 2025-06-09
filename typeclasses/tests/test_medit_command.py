from unittest.mock import MagicMock, patch
from django.test import override_settings
from evennia.utils import create
from evennia.utils.test_resources import EvenniaTest
from commands.admin import BuilderCmdSet
from typeclasses.npcs import BaseNPC


@override_settings(DEFAULT_HOME=None)
class TestMeditCommand(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.char1.msg = MagicMock()
        self.char1.cmdset.add_default(BuilderCmdSet)

    def test_medit_opens_menu(self):
        npc = create.create_object(BaseNPC, key="orc", location=self.room1)
        with patch("commands.mob_builder.EvMenu") as mock_menu:
            self.char1.execute_cmd(f"@medit {npc.key}")
            mock_menu.assert_called_with(self.char1, "commands.npc_builder", startnode="menunode_desc")
            data = self.char1.ndb.buildnpc
            assert data["key"] == "orc"

    def test_medit_invalid(self):
        self.char1.execute_cmd("@medit nowhere")
        assert "Invalid NPC." in self.char1.msg.call_args[0][0]

