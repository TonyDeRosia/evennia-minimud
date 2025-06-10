from unittest.mock import MagicMock, patch
from evennia.utils.test_resources import EvenniaTest
from django.test import override_settings
from commands.admin import BuilderCmdSet
from typeclasses.npcs import BaseNPC
from world.scripts.mob_db import get_mobdb

from commands import builder_types


@override_settings(DEFAULT_HOME=None)
class TestBuilderTypesCommand(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.char1.msg = MagicMock()
        self.char1.cmdset.add_default(BuilderCmdSet)

    def _find(self, key):
        for obj in self.char1.location.contents:
            if obj.key == key:
                return obj
        return None

    def test_command_invokes_helper(self):
        with patch.object(builder_types, "builder_cnpc_prompt") as mock_prompt:
            self.char1.execute_cmd("builder types cnpc gob")
        mock_prompt.assert_called_with(self.char1, "gob")

    def test_prompt_creates_npc_and_vnum(self):
        with patch("utils.vnum_registry.get_next_vnum", return_value=99):
            gen = builder_types.builder_cnpc_prompt(self.char1, "orc")
            next(gen)  # desc prompt
            gen.send("A big orc")
            gen.send("orc")
            gen.send("Warrior")
            gen.send("1")
            try:
                gen.send("yes")
            except StopIteration:
                pass
        npc = self._find("orc")
        self.assertIsNotNone(npc)
        self.assertTrue(npc.is_typeclass(BaseNPC, exact=False))
        self.assertEqual(npc.db.vnum, 99)
        self.assertIsNotNone(get_mobdb().get_proto(99))
