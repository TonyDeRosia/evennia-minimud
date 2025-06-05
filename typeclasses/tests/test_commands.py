"""Tests for custom commands."""

from unittest.mock import MagicMock

from evennia.utils.test_resources import EvenniaTest
from utils.currency import from_copper, to_copper


class TestInfoCommands(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.char1.msg = MagicMock()
        self.char2.msg = MagicMock()
        self.obj1.location = self.char1
        self.char1.db.desc = "A tester."
        self.char2.db.desc = "Another tester."
        self.char1.db.race = "Elf"
        self.char1.db.charclass = "Mage"
        self.char2.db.race = "Human"
        self.char2.db.charclass = "Warrior"

    def test_desc_set_and_view(self):
        self.char1.execute_cmd("desc")
        self.assertTrue(self.char1.msg.called)
        self.char1.msg.reset_mock()
        self.char1.execute_cmd("desc New description")
        self.assertEqual(self.char1.db.desc, "New description")

    def test_finger(self):
        self.char1.execute_cmd(f"finger {self.char2.key}")
        self.assertTrue(self.char1.msg.called)
        output = self.char1.msg.call_args[0][0]
        self.assertIn("╔", output)
        self.assertIn("╚", output)
        self.assertIn("Another tester.", output)
        self.assertIn("Race: Human", output)
        self.assertIn("Class: Warrior", output)
        self.assertIn("No bounty.", output)

    def test_finger_self(self):
        self.char1.execute_cmd("finger self")
        self.assertTrue(self.char1.msg.called)
        output = self.char1.msg.call_args[0][0]
        self.assertIn("╔", output)
        self.assertIn("Race: Elf", output)
        self.assertIn("Class: Mage", output)

    def test_finger_missing_info(self):
        self.char2.db.race = None
        self.char2.db.charclass = None
        self.char1.execute_cmd(f"finger {self.char2.key}")
        output = self.char1.msg.call_args[0][0]
        self.assertIn("Race: Unknown", output)
        self.assertIn("Class: Unknown", output)
        self.assertIn("No bounty.", output)

    def test_finger_bounty(self):
        self.char2.db.title = "The Warrior"
        self.char2.db.guild = "Adventurers Guild"
        self.char2.db.guild_honor = 20
        self.char2.attributes.add("bounty", 10)
        self.char1.execute_cmd(f"finger {self.char2.key}")
        output = self.char1.msg.call_args[0][0]
        self.assertIn("The Warrior", output)
        self.assertIn("Guild: Adventurers Guild", output)
        self.assertIn("Honor: 20", output)
        self.assertIn("Bounty: 10", output)

    def test_score(self):
        self.char1.db.title = "Tester"
        self.char1.db.coins = {
            "copper": 10,
            "silver": 2,
            "gold": 1,
            "platinum": 0,
        }
        self.char1.execute_cmd("score")
        self.assertTrue(self.char1.msg.called)
        args = self.char1.msg.call_args[0][0]
        self.assertIn("Tester", args)
        self.assertIn("COIN POUCH", args)
        self.assertIn("Copper: 10", args)
        self.assertIn("Armor", args)
        self.assertIn("Attack Power", args)
        self.assertIn("╔", args)
        self.assertIn("╚", args)
        self.assertIn("|g", args)
        self.assertIn("|w", args)
        self.assertIn("|c", args)

    def test_score_alias_sc(self):
        self.char1.execute_cmd("sc")
        self.assertTrue(self.char1.msg.called)
        out = self.char1.msg.call_args[0][0]
        self.assertIn("PRIMARY STATS", out)
        self.assertIn("╔", out)

    def test_inventory(self):
        self.char1.execute_cmd("inventory")
        self.assertTrue(self.char1.msg.called)
        self.char1.msg.reset_mock()
        self.obj1.location = self.char1
        self.char1.execute_cmd("inventory")
        self.assertTrue(self.char1.msg.called)

    def test_equipment(self):
        self.char1.attributes.add("_wielded", {"left": self.obj1})
        self.char1.execute_cmd("equipment")
        self.assertTrue(self.char1.msg.called)

    def test_buffs(self):
        self.char1.execute_cmd("buffs")
        self.assertTrue(self.char1.msg.called)
        self.char1.msg.reset_mock()
        self.char1.tags.add("speed", category="buff")
        self.char1.execute_cmd("buffs")
        self.assertTrue(self.char1.msg.called)

    def test_guild(self):
        self.char1.db.guild = "Adventurers Guild"
        self.char1.execute_cmd("guild")
        self.assertTrue(self.char1.msg.called)

    def test_guildwho(self):
        self.char1.db.guild = "Adventurers Guild"
        self.char2.db.guild = "Adventurers Guild"
        self.char1.execute_cmd("guildwho")
        self.assertTrue(self.char1.msg.called)

    def test_who_hides_account(self):
        self.char1.execute_cmd("who")
        self.assertTrue(self.char1.msg.called)
        out = self.char1.msg.call_args[0][0]
        self.assertIn(self.char1.key, out)
        self.assertNotIn(self.char1.account.key, out)


class TestBountySmall(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.char1.db.coins = from_copper(20)
        self.char2.db.coins = from_copper(0)
        self.char2.db.bounty = 0

    def test_bounty_reward_on_defeat(self):
        self.char1.execute_cmd(f"bounty {self.char2.key} 10")
        self.assertEqual(self.char2.db.bounty, 10)
        self.assertEqual(to_copper(self.char1.db.coins), 10)
        self.char2.traits.health.current = 5
        self.char2.at_damage(self.char1, 10)
        self.assertEqual(to_copper(self.char1.db.coins), 20)
        self.assertEqual(self.char2.db.bounty, 0)


class TestBountyLarge(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.char1.db.coins = from_copper(100)
        self.char2.db.coins = from_copper(0)
        self.char2.db.bounty = 0

    def test_bounty_place(self):
        self.char1.execute_cmd(f"bounty {self.char2.key} 30")
        self.assertEqual(to_copper(self.char1.db.coins), 70)
        self.assertEqual(self.char2.db.bounty, 30)

    def test_bounty_reward_on_defeat(self):
        self.char1.execute_cmd(f"bounty {self.char2.key} 10")
        self.assertEqual(self.char2.db.bounty, 10)
        self.assertEqual(to_copper(self.char1.db.coins), 90)  # 100 - 10 bounty
        self.char2.traits.health.current = 5
        self.char2.at_damage(self.char1, 10)
        self.assertEqual(to_copper(self.char1.db.coins), 100)  # Got bounty back
        self.assertEqual(self.char2.db.bounty, 0)

    def test_bounty_claim(self):
        self.char2.db.bounty = 40
        self.char1.db.coins = from_copper(0)
        self.char2.at_damage(self.char1, 200)
        self.assertEqual(to_copper(self.char1.db.coins), 40)
        self.assertEqual(self.char2.db.bounty, 0)
