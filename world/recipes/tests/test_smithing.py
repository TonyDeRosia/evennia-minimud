"""
Tests for smithing recipes

"""

from evennia.utils.test_resources import EvenniaTest
from evennia.contrib.game_systems.crafting import crafting
from world.recipes import smithing
from unittest.mock import patch
from django.conf import settings


class TestSmithingRecipes(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.crafter = self.char2
        self.crafter.traits.add(
            "smithing", "Smithing", trait_type="counter", min=0, max=100
        )
        self.crafter.traits.smithing.base = 20
        if "world.prototypes" not in settings.PROTOTYPE_MODULES:
            settings.PROTOTYPE_MODULES.append("world.prototypes")

    @patch("world.recipes.base.randint", return_value=1)
    def test_ingot(self, mock_randint):
        tools, ingredients = smithing.SmeltIronRecipe.seed()
        results = crafting.craft(self.crafter, "iron ingot", *tools, *ingredients)
        self.assertEqual(results[0].key, "iron ingot")

    @patch("world.recipes.base.randint", return_value=1)
    def test_chainmail_legs(self, mock_randint):
        tools, ingredients = smithing.IronChainmailLegsRecipe.seed()
        results = crafting.craft(self.crafter, "iron chausses", *tools, *ingredients)
        self.assertEqual(results[0].key, "iron chausses")
