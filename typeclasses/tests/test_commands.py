"""Tests for custom commands."""

from unittest.mock import MagicMock

from evennia.utils.test_resources import EvenniaTest
from django.test import override_settings
from utils.currency import from_copper, to_copper


@override_settings(DEFAULT_HOME=None)
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
        self.char2.db.guild_points = {"Adventurers Guild": 20}
        self.char2.db.guild_rank = "Corporal"
        self.char2.attributes.add("bounty", 10)
        self.char1.execute_cmd(f"finger {self.char2.key}")
        output = self.char1.msg.call_args[0][0]
        self.assertIn("The Warrior", output)
        self.assertIn("Guild: Adventurers Guild", output)
        self.assertIn("Guild Points: 20", output)
        self.assertIn("Bounty: 10", output)

    def test_score(self):
        self.char1.db.title = "Tester"
        self.char1.db.copper = 10
        self.char1.db.silver = 2
        self.char1.db.gold = 1
        self.char1.db.platinum = 0
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

    def test_score_shows_gear_bonus(self):
        from evennia.utils import create
        from world.system import stat_manager

        item = create.create_object(
            "typeclasses.objects.ClothingObject",
            key="neck",
            location=self.char1,
        )
        item.tags.add("equipment", category="flag")
        item.tags.add("identified", category="flag")
        item.db.stat_mods = {"STR": 1}
        item.wear(self.char1, True)
        stat_manager.refresh_stats(self.char1)

        self.char1.execute_cmd("score")
        out = self.char1.msg.call_args[0][0]
        self.assertIn("(+1)", out)

    def test_score_shows_multiple_item_bonuses(self):
        from evennia.utils import create

        ring = create.create_object(
            "typeclasses.objects.ClothingObject",
            key="ring",
            location=self.char1,
        )
        ring.tags.add("equipment", category="flag")
        ring.tags.add("identified", category="flag")
        ring.tags.add("jewelry", category="slot")
        ring.db.stat_mods = {"STR": 1}
        ring.wear(self.char1, True)

        armor = create.create_object(
            "typeclasses.objects.ClothingObject",
            key="helm",
            location=self.char1,
        )
        armor.tags.add("equipment", category="flag")
        armor.tags.add("identified", category="flag")
        armor.tags.add("helm", category="slot")
        armor.db.stat_mods = {"CON": 2}
        armor.wear(self.char1, True)

        shield = create.create_object(
            "typeclasses.objects.ClothingObject",
            key="shield",
            location=self.char1,
        )
        shield.tags.add("equipment", category="flag")
        shield.tags.add("identified", category="flag")
        shield.tags.add("shield", category="flag")
        shield.db.stat_mods = {"DEX": 3}
        shield.wear(self.char1, True)

        trinket = create.create_object(
            "typeclasses.objects.ClothingObject",
            key="trinket",
            location=self.char1,
        )
        trinket.tags.add("equipment", category="flag")
        trinket.tags.add("identified", category="flag")
        trinket.tags.add("trinket", category="slot")
        trinket.db.stat_mods = {"WIS": 4}
        trinket.wear(self.char1, True)

        self.char1.execute_cmd("score")
        out = self.char1.msg.call_args[0][0]
        self.assertIn("(+1)", out)
        self.assertIn("(+2)", out)
        self.assertIn("(+3)", out)
        self.assertIn("(+4)", out)

    def test_inventory(self):
        self.char1.execute_cmd("inventory")
        self.assertTrue(self.char1.msg.called)
        self.char1.msg.reset_mock()
        self.obj1.location = self.char1
        self.char1.execute_cmd("inventory")
        self.assertTrue(self.char1.msg.called)

    def test_equipment(self):
        self.char1.attributes.add("_wielded", {"left": None, "right": None})
        self.char1.execute_cmd("equipment")
        out = self.char1.msg.call_args[0][0]
        self.assertIn("Mainhand", out)
        self.assertIn("Offhand", out)
        self.assertIn("Head", out)
        self.assertIn("Jewelry", out)
        self.assertIn("Trinket", out)

    def test_equipment_twohanded(self):
        from evennia.utils import create

        weapon = create.create_object(
            "typeclasses.gear.MeleeWeapon", key="great", location=self.char1
        )
        weapon.tags.add("equipment", category="flag")
        weapon.tags.add("identified", category="flag")

        self.char1.attributes.add("_wielded", {"left": weapon, "right": weapon})
        self.char1.execute_cmd("equipment")
        out = self.char1.msg.call_args[0][0]
        self.assertIn("Twohanded", out)
        self.assertNotIn("Mainhand", out)
        self.assertNotIn("Offhand", out)

    def test_inspect_identified(self):
        self.obj1.db.desc = "A sharp blade."
        self.obj1.db.weight = 2
        self.obj1.db.dmg = 5
        self.obj1.db.slot = "hand"
        self.obj1.db.buff = "speed"
        self.obj1.db.identified = True
        self.obj1.tags.add("equipment", category="flag")
        self.char1.execute_cmd(f"inspect {self.obj1.key}")
        out = self.char1.msg.call_args[0][0]
        self.assertIn("A sharp blade.", out)
        self.assertIn("[ ITEM INFO ]", out)
        self.assertIn("Weight", out)
        self.assertIn("Damage", out)
        self.assertIn("Slot", out)
        self.assertIn("Buffs", out)
        self.assertIn("Flags", out)
        self.assertIn("Identified: yes", out)

    def test_inspect_unidentified(self):
        self.obj1.db.desc = "A mystery item."
        self.obj1.db.identified = False
        self.char1.execute_cmd(f"inspect {self.obj1.key}")
        out = self.char1.msg.call_args[0][0]
        self.assertIn("A mystery item.", out)
        self.assertNotIn("Weight", out)

    def test_inspect_auto_identify(self):
        self.obj1.db.desc = "A hidden gem."
        self.obj1.db.identified = False
        self.obj1.db.required_perception_to_identify = 5
        self.obj1.tags.add("unidentified")
        from world.system import stat_manager
        stat_manager.refresh_stats(self.char1)
        self.char1.execute_cmd(f"inspect {self.obj1.key}")
        out = self.char1.msg.call_args[0][0]
        self.assertIn("Identified: yes", out)

    def test_inspect_admin_bypass(self):
        self.obj1.db.desc = "An enigma."
        self.obj1.db.weight = 3
        self.obj1.db.identified = False
        self.obj1.tags.add("unidentified")
        self.obj1.db.required_perception_to_identify = 50
        self.char1.permissions.add("Builder")
        self.char1.execute_cmd(f"inspect {self.obj1.key}")
        out = self.char1.msg.call_args[0][0]
        self.assertIn("Identified: no", out)
        self.assertIn("Weight", out)

    def test_inspect_alias_exact_match(self):
        from evennia.utils import create

        w1 = create.create_object(
            "typeclasses.gear.MeleeWeapon", key="epee-1", location=self.char1
        )
        w1.aliases.add("epee-1")
        w1.db.dmg = 1
        w1.db.slot = "mainhand"
        w1.db.identified = True

        w2 = create.create_object(
            "typeclasses.gear.MeleeWeapon", key="epee-10", location=self.char1
        )
        w2.aliases.add("epee-10")
        w2.db.dmg = 10
        w2.db.slot = "mainhand"
        w2.tags.add("flaming", category="buff")
        w2.tags.add("STR+2")
        w2.db.identified = True

        self.char1.msg.reset_mock()
        self.char1.execute_cmd("inspect epee-1")
        out = self.char1.msg.call_args[0][0]
        self.assertIn("Damage", out)
        self.assertIn("mainhand", out)
        self.assertNotIn("epee-1", out)
        self.char1.msg.reset_mock()

        self.char1.execute_cmd("inspect epee-10")
        out = self.char1.msg.call_args[0][0]
        self.assertIn("Damage", out)
        self.assertIn("flaming", out)
        self.assertIn("STR+2", out)
        self.assertNotIn("epee-10", out)

    def test_inspect_duplicate_named_weapons(self):
        """Ensure inspect selects the correct weapon when names repeat."""

        self.char1.execute_cmd("cweapon epee mainhand 1d4 first")
        self.char1.execute_cmd("cweapon epee mainhand 2d5 second")
        self.char1.execute_cmd("cweapon epee offhand 3d6 third")

        w1 = next(o for o in self.char1.contents if "epee-1" in list(o.aliases.all()))
        w2 = next(o for o in self.char1.contents if "epee-2" in list(o.aliases.all()))
        w3 = next(o for o in self.char1.contents if "epee-3" in list(o.aliases.all()))

        w2.tags.add("flaming", category="buff")
        w2.tags.add("STR+2")
        w3.tags.add("chilling", category="buff")
        w1.db.identified = True
        w2.db.identified = True
        w3.db.identified = True
        w1.db.slot = "mainhand"
        w2.db.slot = "mainhand"
        w3.db.slot = "offhand"

        self.char1.msg.reset_mock()
        self.char1.execute_cmd("inspect epee-2")
        out = self.char1.msg.call_args[0][0]
        self.assertIn("2d5", out)
        self.assertIn("mainhand", out)
        self.assertIn("flaming", out)
        self.assertNotIn("epee-2", out)

        self.char1.msg.reset_mock()
        self.char1.execute_cmd("inspect epee-3")
        out = self.char1.msg.call_args[0][0]
        self.assertIn("3d6", out)
        self.assertIn("offhand", out)
        self.assertIn("chilling", out)
        self.assertNotIn("epee-3", out)

    def test_inspect_shows_bonuses(self):
        self.char1.execute_cmd(
            "cweapon longsword mainhand 3d10 5 STR+2, Attack Power+5 A sharp blade."
        )
        weapon = next(o for o in self.char1.contents if "longsword" in o.key.lower())
        weapon.db.identified = True
        self.char1.msg.reset_mock()
        self.char1.execute_cmd("inspect longsword")
        out = self.char1.msg.call_args[0][0]
        self.assertIn("Bonuses:", out)
        self.assertIn("STR +2", out)
        self.assertIn("Attack Power +5", out)

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


class TestRemoveCommand(EvenniaTest):
    def test_remove_returns_to_inventory(self):
        from evennia.utils import create

        item = create.create_object(
            "typeclasses.objects.ClothingObject",
            key="cap",
            location=self.char1,
        )
        item.tags.add("equipment", category="flag")
        item.tags.add("identified", category="flag")
        item.tags.add("helm", category="slot")
        item.wear(self.char1, True)
        self.assertTrue(item.db.worn)
        self.assertIsNone(item.location)

        self.char1.execute_cmd(f"remove {item.key}")
        self.assertFalse(item.db.worn)
        self.assertEqual(item.location, self.char1)

    def test_remove_partial_and_alias(self):
        from evennia.utils import create

        item = create.create_object(
            "typeclasses.objects.ClothingObject",
            key="|gbright cap|n",
            location=self.char1,
        )
        item.aliases.add("capper")
        item.tags.add("equipment", category="flag")
        item.tags.add("identified", category="flag")
        item.tags.add("helm", category="slot")
        item.wear(self.char1, True)

        # partial key
        self.char1.execute_cmd("remove bright")
        self.assertFalse(item.db.worn)
        self.assertEqual(item.location, self.char1)

        item.wear(self.char1, True)
        # alias
        self.char1.execute_cmd("remove capper")
        self.assertFalse(item.db.worn)
        self.assertEqual(item.location, self.char1)


class TestRemoveAllCommand(EvenniaTest):
    def test_remove_all_removes_everything(self):
        from evennia.utils import create

        armor = create.create_object(
            "typeclasses.objects.ClothingObject",
            key="cap",
            location=self.char1,
        )
        armor.tags.add("equipment", category="flag")
        armor.tags.add("identified", category="flag")
        armor.tags.add("helm", category="slot")
        armor.wear(self.char1, True)

        weapon = create.create_object(
            "typeclasses.gear.MeleeWeapon", key="stick", location=self.char1
        )
        weapon.tags.add("equipment", category="flag")
        weapon.tags.add("identified", category="flag")
        weapon.db.slot = "mainhand"
        self.char1.attributes.add("_wielded", {"left": None, "right": None})
        self.char1.at_wield(weapon)

        self.char1.execute_cmd("remove all")
        self.assertFalse(armor.db.worn)
        self.assertEqual(armor.location, self.char1)
        self.assertNotIn(weapon, self.char1.wielding)
        self.assertEqual(weapon.location, self.char1)


class TestDigCommand(EvenniaTest):
    def test_dig_creates_room_and_exits(self):
        start = self.char1.location
        self.char1.execute_cmd("dig north")
        new_room = start.db.exits.get("north")
        self.assertIsNotNone(new_room)
        back = new_room.db.exits.get("south")
        self.assertEqual(back, start)
        self.char1.execute_cmd("north")
        self.assertEqual(self.char1.location, new_room)
        self.char1.execute_cmd("south")
        self.assertEqual(self.char1.location, start)

    def test_dig_sets_area_and_room_id(self):
        start = self.char1.location
        start.set_area("test", 1)
        self.char1.execute_cmd("dig east test 2")
        new_room = start.db.exits.get("east")
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
        new_room = start.db.exits.get("north")
        self.assertEqual(new_room.db.area, "test")
        self.assertEqual(new_room.db.room_id, 2)

    def test_teleport_to_area_room(self):
        start = self.char1.location
        self.char1.execute_cmd("dig east=test:3")
        target = start.db.exits.get("east")
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

    def test_rrename_changes_room_name(self):
        start = self.char1.location
        self.char1.execute_cmd("rrename New Room")
        self.assertEqual(start.key, "New Room")

    def test_rrename_usage(self):
        self.char1.execute_cmd("rrename")
        self.char1.msg.assert_called_with("Usage: rrename <new name>")


class TestRoomDescCommand(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.char1.msg = MagicMock()

    def test_rdesc_sets_room_description(self):
        self.char1.execute_cmd("rdesc A dark cavern")
        self.assertEqual(self.char1.location.db.desc, "A dark cavern")

    def test_rdesc_shows_description(self):
        self.char1.location.db.desc = "Some desc"
        self.char1.execute_cmd("rdesc")
        self.char1.msg.assert_called_with("Some desc")


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

    def test_setstat_derived(self):
        self.char1.execute_cmd(f"setstat {self.char2.key} attack_power 50")
        self.assertEqual(self.char2.db.stat_overrides.get("attack_power"), 50)
        self.assertEqual(self.char2.db.derived_stats.get("attack_power"), 50)

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


class TestFlagCommands(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.char1.msg = MagicMock()

    def test_setflag_and_removeflag(self):
        self.char1.execute_cmd(f"setflag {self.obj1.key} equipment")
        self.assertTrue(self.obj1.tags.has("equipment", category="flag"))
        self.char1.execute_cmd(f"removeflag {self.obj1.key} equipment")
        self.assertFalse(self.obj1.tags.has("equipment", category="flag"))
