from unittest.mock import MagicMock, patch
from evennia.utils.test_resources import EvenniaTest
from evennia.utils import create
from django.conf import settings

from world.quests import Quest, QuestManager
from world.recipes import smithing
from commands.shops import CmdDonate


class TestExperienceAnnouncements(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.char1.msg = MagicMock()
        if "world.prototypes" not in settings.PROTOTYPE_MODULES:
            settings.PROTOTYPE_MODULES.append("world.prototypes")
        # ensure crafting skill
        self.char1.traits.add("smithing", trait_type="counter", min=0, max=100)
        self.char1.traits.smithing.base = 5

    @patch("evennia.contrib.game_systems.crafting.crafting.CraftingRecipe.craft", return_value=[])
    @patch("world.recipes.base.randint", return_value=1)
    def test_crafting_announces_xp(self, mock_rand, mock_super):
        recipe = smithing.SmeltIronRecipe()
        recipe.crafter = self.char1
        recipe.msg = MagicMock()
        recipe.craft()
        messages = [call.args[0] for call in self.char1.msg.call_args_list]
        assert "You gain |Y1|n experience points!" in messages

    def test_quest_complete_announces_xp(self):
        quest = Quest(quest_key="testquest", title="Q", goal_type="kill", amount=1, xp_reward=5)
        QuestManager.save(quest)
        self.char1.db.active_quests = {"testquest": {"progress": 1}}
        self.char1.execute_cmd("complete testquest")
        messages = [call.args[0] for call in self.char1.msg.call_args_list]
        assert "You gain |Y5|n experience points!" in messages

    def test_donate_announces_xp(self):
        from typeclasses.rooms import XYGridShop

        shop = create.create_object(XYGridShop, key="shop")
        shop.db.donation_tags = ["ore"]
        item = create.create_object("typeclasses.objects.Object", key="ore", location=self.char1)
        item.tags.add("ore", category="crafting_material")
        item.db.value = 10

        cmd = CmdDonate()
        cmd.caller = self.char1
        cmd.obj = shop
        cmd.args = "ore"
        cmd.count = 1
        cmd.parse()
        self.char1.search = MagicMock(return_value=item)
        gen = cmd.func()
        next(gen)
        try:
            gen.send("yes")
        except StopIteration:
            pass
        messages = [call.args[0] for call in self.char1.msg.call_args_list]
        assert "You gain |Y5|n experience points!" in messages
