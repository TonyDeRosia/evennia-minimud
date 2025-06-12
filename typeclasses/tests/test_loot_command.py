"""Tests for the loot command."""

from unittest.mock import MagicMock
from django.test import override_settings
from evennia.utils import create
from evennia.utils.test_resources import EvenniaTest


@override_settings(DEFAULT_HOME=None)
class TestCmdLoot(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.char1.msg = MagicMock()

    def test_loot_moves_items(self):
        from typeclasses.characters import NPC

        npc = create.create_object(NPC, key="mob", location=self.room1)
        item = create.create_object("typeclasses.objects.Object", key="loot", location=npc)
        npc.db.drops = []
        npc.traits.health.current = 1
        npc.at_damage(self.char1, 2)

        corpse = next(
            obj for obj in self.room1.contents
            if obj.is_typeclass("typeclasses.objects.Corpse", exact=False)
        )

        self.char1.execute_cmd(f"loot {corpse.key}")

        assert item.location == self.char1
