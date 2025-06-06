from unittest.mock import MagicMock

from evennia import create_object
from commands.admin import AdminCmdSet
from commands.default_cmdsets import CharacterCmdSet
from evennia.utils.test_resources import EvenniaTest
from django.test import override_settings
from typeclasses.characters import PlayerCharacter
from typeclasses.objects import Object


@override_settings(DEFAULT_HOME=None)
class TestAdminCommands(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.char1.msg = MagicMock()
        self.char2.msg = MagicMock()
        # ensure commands are available even when characters are offline
        self.char1.cmdset.add_default(AdminCmdSet)
        self.char2.cmdset.add_default(AdminCmdSet)
        # extra room setup for scan command
        self.room2.db.desc = "Another room"
        self.room2.tags.add("dark", category="room_flag")
        self.room2.tags.add("ruins")
        self.obj1.location = self.room2
        self.char_other = create_object(
            PlayerCharacter, key="OtherChar", location=self.room2, home=self.room2
        )
        self.char_other.cmdset.add_default(CharacterCmdSet)

    def test_setstat_and_setattr_offline(self):
        offline = create_object(PlayerCharacter, key="Offline", location=self.room1, home=self.room1)
        self.char1.execute_cmd(f"setstat {offline.key} STR 15")
        self.assertEqual(offline.traits.STR.base, 15)
        self.char1.execute_cmd(f"setattr {offline.key} foo bar")
        self.assertEqual(offline.db.foo, "bar")

    def test_slay_clears_bounty(self):
        self.char2.db.bounty = 10
        self.char1.execute_cmd(f"slay {self.char2.key}")
        self.assertEqual(self.char2.traits.health.current, 0)
        self.assertTrue(self.char2.tags.has("unconscious", category="status"))
        self.assertEqual(self.char2.db.bounty, 0)

    def test_smite(self):
        self.char2.traits.health.current = 20
        self.char1.execute_cmd(f"smite {self.char2.key}")
        self.assertEqual(self.char2.traits.health.current, 1)

    def test_scan_player_vs_admin(self):
        self.char2.execute_cmd("scan")
        player_out = self.char2.msg.call_args[0][0]
        self.assertNotIn("Room flags:", player_out)
        self.assertNotIn("Tags:", player_out)
        self.char1.execute_cmd("scan")
        admin_out = self.char1.msg.call_args[0][0]
        self.assertIn("Room flags: dark", admin_out)
        self.assertIn("Tags: ruins", admin_out)
        self.assertIn("HP", admin_out)

    def test_help_entries_exist(self):
        for cmd in ("slay", "smite", "setstat", "setattr", "scan", "restoreall"):
            self.char1.msg.reset_mock()
            self.char1.execute_cmd(f"help {cmd}")
            self.assertTrue(self.char1.msg.called)

    def test_restoreall(self):
        self.char1.traits.health.current = 10
        self.char2.traits.mana.current = 5
        self.char1.tags.add("speed", category="buff")
        self.char2.tags.add("sleeping", category="status")
        self.char_other.traits.stamina.current = 1
        self.char1.execute_cmd("restoreall")
        for pc in (self.char1, self.char2, self.char_other):
            self.assertEqual(pc.traits.health.current, pc.traits.health.max)
            self.assertEqual(pc.traits.mana.current, pc.traits.mana.max)
            self.assertEqual(pc.traits.stamina.current, pc.traits.stamina.max)
            self.assertFalse(pc.tags.get(category="buff", return_list=True))
            self.assertFalse(pc.tags.get(category="status", return_list=True))


    def test_revive_all(self):
        for pc in (self.char2, self.char_other):
            pc.tags.add("unconscious", category="status")
            pc.tags.add("lying down", category="status")
            pc.traits.health.current = 0
        from commands.combat import CmdRevive
        cmd = CmdRevive()
        cmd.caller = self.char1
        cmd.args = "all"
        cmd.msg = MagicMock()
        cmd.func()
        for pc in (self.char2, self.char_other):
            self.assertFalse(pc.tags.has("unconscious", category="status"))
            self.assertEqual(pc.traits.health.current, pc.traits.health.max // 5)

    def test_purge_deletes_objects(self):
        obj1 = create_object(Object, key="trash", location=self.room1)
        obj2 = create_object(Object, key="garbage", location=self.room1)
        self.char1.location = self.room1
        self.char1.execute_cmd("purge")
        self.assertIsNone(obj1.pk)
        self.assertIsNone(obj2.pk)

    def test_purge_target(self):
        obj = create_object(Object, key="target", location=self.room1)
        self.char1.execute_cmd("purge target")
        self.assertIsNone(obj.pk)

    def test_cweapon_dice_and_slot(self):
        self.char1.execute_cmd("cweapon dagger mainhand/offhand 3d7")
        weapon = next((obj for obj in self.char1.contents if "dagger" in list(obj.aliases.all())), None)
        self.assertIsNotNone(weapon)
        self.assertTrue(weapon.tags.has("mainhand", category="flag"))
        self.assertTrue(weapon.tags.has("offhand", category="flag"))
        self.assertEqual(weapon.db.damage_dice, "3d7")
        self.assertEqual(weapon.db.dice_num, 3)
        self.assertEqual(weapon.db.dice_sides, 7)

    def test_cweapon_duplicate_names_numbered_aliases(self):
        """Creating weapons with the same name should give numbered aliases."""

        from commands.admin import CmdCWeapon

        cmd = CmdCWeapon()
        cmd.caller = self.char1
        cmd.args = "Epee mainhand 1d4 A thin blade"
        cmd.func()

        cmd = CmdCWeapon()
        cmd.caller = self.char1
        cmd.args = "epee offhand 2d6 A second blade"
        cmd.func()

        w1 = next((o for o in self.char1.contents if "epee-1" in list(o.aliases.all())), None)
        w2 = next((o for o in self.char1.contents if "epee-2" in list(o.aliases.all())), None)

        self.assertIsNotNone(w1)
        self.assertIsNotNone(w2)

        self.assertEqual(w1.key, "Epee")
        self.assertEqual(w2.key, "Epee")

        self.assertIn("epee", w1.aliases.all())
        self.assertIn("epee", w2.aliases.all())
        self.assertIn("epee-1", w1.aliases.all())
        self.assertIn("epee-2", w2.aliases.all())

        self.assertEqual(w1.db.desc, "A thin blade")
        self.assertEqual(w2.db.desc, "A second blade")

        self.assertEqual(w1.db.damage_dice, "1d4")
        self.assertEqual(w2.db.damage_dice, "2d6")

    def test_cweapon_tags_and_wield(self):
        """Weapon created with cweapon should get tags and be wieldable."""

        self.char1.execute_cmd("cweapon axe mainhand 5")
        weapon = next(
            (o for o in self.char1.contents if "axe" in list(o.aliases.all())),
            None,
        )
        self.assertIsNotNone(weapon)
        self.assertTrue(weapon.tags.has("equipment", category="flag"))
        self.assertTrue(weapon.tags.has("identified", category="flag"))
        self.assertTrue(weapon.tags.has("mainhand", category="flag"))
        self.assertTrue(weapon.tags.has("mainhand", category="slot"))
        self.char1.attributes.add("_wielded", {"left": None, "right": None})
        hands = self.char1.at_wield(weapon)
        self.assertTrue(hands)
        self.assertIn(weapon, self.char1.wielding)

    def test_carmor_tags_and_wear(self):
        """Armor created with carmor gets tags and can be worn."""

        self.char1.execute_cmd("carmor helm head 1")
        armor = next(
            (o for o in self.char1.contents if "helm" in list(o.aliases.all())),
            None,
        )
        self.assertIsNotNone(armor)
        self.assertTrue(armor.tags.has("equipment", category="flag"))
        self.assertTrue(armor.tags.has("identified", category="flag"))
        self.assertTrue(armor.tags.has("head", category="slot"))
        armor.wear(self.char1, True)
        self.assertTrue(armor.db.worn)

    def test_cshield_flags_and_blocks_twohanded(self):
        """Shield created with cshield should get shield flag and block two-handed weapons."""

        self.char1.execute_cmd("cshield buckler offhand 1")
        shield = next((o for o in self.char1.contents if "buckler" in list(o.aliases.all())), None)
        self.assertIsNotNone(shield)
        self.assertTrue(shield.tags.has("shield", category="flag"))
        shield.wear(self.char1, True)
        self.assertTrue(shield.db.worn)

        self.char1.attributes.add("_wielded", {"left": None, "right": None})
        weapon = create_object("typeclasses.gear.MeleeWeapon", key="great", location=self.char1)
        weapon.tags.add("equipment", category="flag")
        weapon.tags.add("identified", category="flag")
        weapon.tags.add("twohanded", category="flag")
        self.assertIsNone(self.char1.at_wield(weapon))
        self.assertNotIn(weapon, self.char1.wielding)

    def test_cring_and_ctrinket_wear_and_display(self):
        """Rings and trinkets created by builders can be worn and show in equipment."""

        self.char1.execute_cmd("cring ruby")
        ring = next((o for o in self.char1.contents if "ruby" in list(o.aliases.all())), None)
        self.assertIsNotNone(ring)
        ring.wear(self.char1, True)
        self.assertTrue(ring.db.worn)

        self.char1.msg.reset_mock()
        self.char1.execute_cmd("equipment")
        out = self.char1.msg.call_args[0][0]
        self.assertIn("Ring1", out)
        self.assertIn("ruby", out.lower())

        self.char1.execute_cmd("ctrinket charm")
        trinket = next((o for o in self.char1.contents if "charm" in list(o.aliases.all())), None)
        self.assertIsNotNone(trinket)
        trinket.wear(self.char1, True)
        self.assertTrue(trinket.db.worn)

        self.char1.msg.reset_mock()
        self.char1.execute_cmd("equipment")
        out = self.char1.msg.call_args[0][0]
        self.assertIn("Accessory", out)
        self.assertIn("charm", out.lower())
