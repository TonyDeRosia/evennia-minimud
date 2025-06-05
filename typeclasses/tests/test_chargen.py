from evennia.utils.test_resources import EvenniaTest
from evennia import create_object
from django.test import override_settings
from world import chargen_menu


@override_settings(DEFAULT_HOME="#1")
class TestChargen(EvenniaTest):
    def setUp(self):
        super().setUp()
        # Create a placeholder character for the chargen process
        self.char = create_object(
            "typeclasses.characters.PlayerCharacter",
            key="In Progress",
            location=None,
            home=self.room1,
        )
        self.account.ndb.new_char = self.char

    def test_set_race_initializes_attributes(self):
        chargen_menu._set_race(self.account, "", "Human")
        self.assertEqual(self.char.db.race, "Human")
        self.assertIsNone(self.char.db.charclass)
        for stat in chargen_menu.STAT_LIST:
            self.assertEqual(self.char.attributes.get(stat.lower()), 0)

    def test_allocate_and_finalize(self):
        chargen_menu._set_race(self.account, "", "Human")
        chargen_menu._set_class(self.account, "", "Warrior")
        chargen_menu._set_gender(self.account, "", "male")

        chargen_menu._adjust_stat(self.account, "", "STR", 2)
        chargen_menu._adjust_stat(self.account, "", "CON", 1)
        chargen_menu._adjust_stat(self.account, "", "DEX", 1)
        chargen_menu._adjust_stat(self.account, "", "INT", 1)
        chargen_menu._adjust_stat(self.account, "", "WIS", 1)
        chargen_menu._adjust_stat(self.account, "", "LUCK", 1)

        expected = {
            stat: self.char.attributes.get(stat.lower(), default=0)
            for stat in chargen_menu.STAT_LIST
        }

        chargen_menu.menunode_finish(self.account)

        for stat in chargen_menu.STAT_LIST:
            trait = self.char.traits.get(stat)
            self.assertIsNotNone(trait)
            self.assertEqual(trait.base, expected[stat])

        self.assertEqual(self.char.db.race, "Human")
        self.assertEqual(self.char.db.charclass, "Warrior")
        self.assertEqual(self.char.db.gender, "male")

    def test_adjust_stat_manual_adds_points(self):
        chargen_menu._set_race(self.account, "", "Human")
        chargen_menu._set_class(self.account, "", "Warrior")
        chargen_menu._set_gender(self.account, "", "male")

        base_str = self.char.attributes.get("str")
        chargen_menu._adjust_stat_manual(self.account, "STR 5")
        self.assertEqual(self.char.attributes.get("str"), base_str + 5)

        # Reset should restore base values
        chargen_menu._reset_stats(self.account)
        self.assertEqual(self.char.attributes.get("str"), base_str)
