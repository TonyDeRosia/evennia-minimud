from evennia.utils import create
from evennia.utils.test_resources import EvenniaTest
from typeclasses.npcs import BaseNPC
from world import area_npcs


class TestNPCSearchUtilities(EvenniaTest):
    def test_search_by_prototype_and_area(self):
        npc = create.create_object(BaseNPC, key="mob", location=self.room1)
        npc.db.prototype_key = "goblin"
        npc.db.area_tag = "dungeon"

        by_proto = area_npcs.find_npcs_by_prototype("goblin")
        self.assertIn(npc, by_proto)

        by_area = area_npcs.find_npcs_by_area("dungeon")
        self.assertIn(npc, by_area)
