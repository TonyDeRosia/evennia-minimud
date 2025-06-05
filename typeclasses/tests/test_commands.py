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
        self.assertIn("+", output)
        self.assertIn("=", output)
        self.assertIn("Another tester.", output)
        self.assertIn("Race: Human", output)
        self.assertIn("Class: Warrior", output)
        self.assertIn("No bounty.", output)

    def test_finger_self(self):
        self.char1.execute_cmd("finger self")
        self.assertTrue(self.char1.msg.called)
        output = self.char1.msg.call_args[0][0]
        self.assertIn("+", output)
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
        self.assertIn("+", args)
        self.assertIn("=", args)
        self.assertIn("|g", args)
        self.assertIn("|w", args)
        self.assertIn("|c", args)

    def test_score_alias_sc(self):
        self.char1.execute_cmd("sc")
        self.assertTrue(self.char1.msg.called)
        out = self.char1.msg.call_args[0][0]
        self.assertIn("PRIMARY STATS", out)
        self.assertIn("+", out)

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
        self.char1.db.temp_bonuses = {"STR": [{"amount": 5, "duration": 3}]}
        self.char1.execute_cmd("buffs")
        out = self.char1.msg.call_args[0][0]
        self.assertIn("Speed Boost", out)
        self.assertIn("Strength Bonus", out)
        self.assertIn("3", out)

    def test_affects(self):
        self.char1.db.status_effects = {"stunned": 5}
        self.char1.tags.add("speed", category="buff")
        self.char1.db.temp_bonuses = {"STR": [{"amount": 5, "duration": 3}]}
        self.char1.execute_cmd("affects")
        out = self.char1.msg.call_args[0][0]
        self.assertIn("Stunned", out)
        self.assertIn("Speed Boost", out)
        self.assertIn("Strength Bonus", out)
        self.assertIn("5", out)
        self.assertIn("3", out)

    def test_affects_uses_effect_key_for_stat_bonus(self):
        self.char1.msg.reset_mock()
        from world.system import state_manager

        state_manager.add_temp_stat_bonus(
            self.char1, "STR", 2, 3, effect_key="speed"
        )
        self.char1.execute_cmd("affects")
        out = self.char1.msg.call_args[0][0]
        self.assertIn("Speed Boost", out)
        self.assertNotIn("Strength Bonus", out)

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


class TestCommandPrompt(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.char1.refresh_prompt = MagicMock()

    def test_command_refreshes_prompt(self):
        self.char1.execute_cmd("score")
        self.char1.refresh_prompt.assert_called_once()

    def test_look_refreshes_prompt(self):
        self.char1.execute_cmd("look")
        self.char1.refresh_prompt.assert_called_once()


class TestReturnAppearance(EvenniaTest):
    def test_room_return_appearance_format(self):
        self.room1.appearance_template = (
            "╔{name}\n{desc}\n{exits}\n{characters}\n{things}\n╚"
        )
        output = self.room1.return_appearance(self.char1)
        self.assertIn("╔", output)
        self.assertIn("╚", output)
        self.assertIn("|wExits:|n", output)
        self.assertIn("|wCharacters:|n", output)
        self.assertIn("|wYou see:|n", output)


class TestRestCommands(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.char1.msg = MagicMock()

    def test_rest_adds_status(self):
        self.char1.execute_cmd("rest")
        self.assertTrue(self.char1.tags.has("sitting", category="status"))

    def test_sleep_adds_statuses(self):
        self.char1.execute_cmd("sleep")
        self.assertTrue(self.char1.tags.has("sleeping", category="status"))
        self.assertTrue(self.char1.tags.has("lying down", category="status"))

    def test_wake_removes_statuses(self):
        self.char1.tags.add("sleeping", category="status")
        self.char1.tags.add("lying down", category="status")
        self.char1.tags.add("sitting", category="status")
        self.char1.execute_cmd("wake")
        self.assertFalse(self.char1.tags.has("sleeping", category="status"))
        self.assertFalse(self.char1.tags.has("lying down", category="status"))
        self.assertFalse(self.char1.tags.has("sitting", category="status"))

    def test_look_while_sleeping(self):
        self.char1.tags.add("sleeping", category="status")
        self.char1.execute_cmd("look")
        self.char1.msg.assert_any_call("You can't see anything with your eyes closed.")


class TestDigCommand(EvenniaTest):
    def test_dig_creates_room_and_exits(self):
        start = self.char1.location
        self.char1.execute_cmd("dig north")
        new_exit = start.exits.get(key="north")
        self.assertIsNotNone(new_exit)
        self.assertIn("n", list(new_exit.aliases.all()))
        new_room = new_exit.destination
        back_exit = new_room.exits.get(key="south")
        self.assertIsNotNone(back_exit)
        self.assertIn("s", list(back_exit.aliases.all()))
        self.char1.execute_cmd("north")
        self.assertEqual(self.char1.location, new_room)
        self.char1.execute_cmd("south")
        self.assertEqual(self.char1.location, start)

    def test_dig_sets_area_and_room_id(self):
        start = self.char1.location
        start.set_area("test", 1)
        self.char1.execute_cmd("dig east test 2")
        new_room = start.exits.get(key="east").destination
        self.assertEqual(new_room.db.area, "test")
        self.assertEqual(new_room.db.room_id, 2)


class TestAreaMakeCommand(EvenniaTest):
    def test_amake_sets_area_on_room(self):
        self.char1.execute_cmd("amake foo 1-5")
        self.assertEqual(self.char1.location.db.area, "foo")
        self.assertEqual(self.char1.location.db.room_id, 1)


class TestExtendedDigTeleport(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.char1.execute_cmd("amake test 1-5")

    def test_dig_eq_syntax(self):
        start = self.char1.location
        self.char1.execute_cmd("dig north=test:2")
        new_room = start.exits.get(key="north").destination
        self.assertEqual(new_room.db.area, "test")
        self.assertEqual(new_room.db.room_id, 2)

    def test_teleport_to_area_room(self):
        start = self.char1.location
        self.char1.execute_cmd("dig east=test:3")
        target = start.exits.get(key="east").destination
        self.char1.execute_cmd("@teleport test:3")
        self.assertEqual(self.char1.location, target)
        # out of range should not move
        self.char1.location = start
        self.char1.execute_cmd("@teleport test:6")
        self.assertEqual(self.char1.location, start)


class TestRoomFlagCommands(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.char1.msg = MagicMock()

    def test_rflags_empty(self):
        self.char1.execute_cmd("rflags")
        self.char1.msg.assert_called_with("This room has no flags.")

    def test_rflag_add_and_remove(self):
        self.char1.execute_cmd("rflag add dark")
        self.assertTrue(self.char1.location.tags.has("dark", category="room_flag"))
        self.char1.execute_cmd("rflags")
        out = self.char1.msg.call_args[0][0]
        self.assertIn("dark", out)
        self.char1.execute_cmd("rflag remove dark")
        self.assertFalse(self.char1.location.tags.has("dark", category="room_flag"))


class TestRoomRenameCommand(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.char1.msg = MagicMock()

    def test_rname_changes_room_name(self):
        start = self.char1.location
        self.char1.execute_cmd("rname New Room")
        self.assertEqual(start.key, "New Room")

    def test_rname_usage(self):
        self.char1.execute_cmd("rname")
        self.char1.msg.assert_called_with("Usage: rname <new name>")


class TestRoomSetCommand(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.char1.msg = MagicMock()

    def test_rset_area(self):
        self.char1.execute_cmd("rset area test")
        self.assertEqual(self.char1.location.db.area, "test")

    def test_rset_id_validation(self):
        self.char1.execute_cmd("amake test 1-5")
        self.char1.msg.reset_mock()
        self.char1.execute_cmd("dig north test 2")
        self.char1.execute_cmd("rset id 2")
        self.char1.msg.assert_called_with("Room already exists.")
        self.char1.msg.reset_mock()
        self.char1.execute_cmd("rset id 6")
        self.char1.msg.assert_called_with("Number outside area range.")


class TestAdminCommands(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.char1.msg = MagicMock()
        self.char2.msg = MagicMock()

    def test_setstat_core(self):
        self.char1.execute_cmd(f"setstat {self.char2.key} STR 12")
        self.assertEqual(self.char2.traits.STR.base, 12)

    def test_setattr_and_bounty(self):
        self.char1.execute_cmd(f"setattr {self.char2.key} testattr foo")
        self.assertEqual(self.char2.db.testattr, "foo")
        self.char1.execute_cmd(f"setbounty {self.char2.key} 5")
        self.assertEqual(self.char2.db.bounty, 5)

    def test_smite_and_slay(self):
        self.char2.traits.health.current = 50
        self.char1.execute_cmd(f"smite {self.char2.key}")
        self.assertEqual(self.char2.traits.health.current, 1)
        self.char1.execute_cmd(f"slay {self.char2.key}")
        self.assertEqual(self.char2.traits.health.current, 0)
        self.assertTrue(self.char2.tags.has("unconscious", category="status"))
