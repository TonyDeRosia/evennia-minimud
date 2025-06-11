from unittest.mock import MagicMock, patch
from django.test import override_settings
from evennia.utils import create
from evennia.utils.test_resources import EvenniaTest
from commands.admin import BuilderCmdSet
from typeclasses.npcs import BaseNPC


@override_settings(DEFAULT_HOME=None)
class TestEditNPCCommand(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.char1.msg = MagicMock()
        self.char1.cmdset.add_default(BuilderCmdSet)

    def test_editnpc_opens_menu(self):
        npc = create.create_object(BaseNPC, key="orc", location=self.room1)
        with patch("commands.npc_builder.EvMenu") as mock_menu:
            self.char1.execute_cmd(f"@editnpc {npc.key}")
            mock_menu.assert_called_with(
                self.char1,
                "commands.npc_builder",
                startnode="menunode_review",
                cmd_on_exit=npc_builder._on_menu_exit,
            )
            data = self.char1.ndb.buildnpc
            assert data["key"] == "orc"

    def test_editnpc_invalid(self):
        self.char1.execute_cmd("@editnpc nowhere")
        assert "Invalid NPC." in self.char1.msg.call_args[0][0]

