from unittest.mock import MagicMock

from evennia import create_object
from evennia.utils.ansi import strip_ansi
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
        offline = create_object(
            PlayerCharacter, key="Offline", location=self.room1, home=self.room1
        )
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
        self.char1.execute_cmd("cweapon dagger mainhand/offhand 3d7 2 test")
        weapon = next(
            (obj for obj in self.char1.contents if "dagger" in list(obj.aliases.all())),
            None,
        )
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
        cmd.args = "Epee mainhand 1d4 1 A thin blade"
        cmd.func()

        cmd = CmdCWeapon()
        cmd.caller = self.char1
        cmd.args = "epee offhand 2d6 1 A second blade"
        cmd.func()

        w1 = next(
            (o for o in self.char1.contents if "epee-1" in list(o.aliases.all())), None
        )
        w2 = next(
            (o for o in self.char1.contents if "epee-2" in list(o.aliases.all())), None
        )

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

        self.char1.execute_cmd("cweapon axe mainhand 5 2 sharp")
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

    def test_cweapon_unidentified(self):
        """Weapon can be created as unidentified."""

        self.char1.execute_cmd("cweapon /unidentified dagger mainhand 3 1 test")
        weapon = next(
            (o for o in self.char1.contents if "dagger" in list(o.aliases.all())),
            None,
        )
        self.assertIsNotNone(weapon)
        self.assertTrue(weapon.tags.has("unidentified", category="flag"))
        self.assertFalse(weapon.tags.has("identified", category="flag"))
        self.assertFalse(weapon.db.identified)

    def test_cweapon_with_stat_mods(self):
        """Weapon creation supports stat modifiers and description parsing."""

        self.char1.execute_cmd(
            "cweapon longsword mainhand 3d10 5 STR+2, Attack Power+5, Hit Chance+3 A vicious longsword."
        )
        weapon = next(
            (
                o
                for o in self.char1.contents
                if "longsword" in [al.lower() for al in o.aliases.all()]
            ),
            None,
        )
        self.assertIsNotNone(weapon)
        self.assertEqual(weapon.db.weight, 5)
        self.assertEqual(
            weapon.db.stat_mods,
            {"str": 2, "attack_power": 5, "hit_chance": 3},
        )
        self.assertEqual(weapon.db.desc, "A vicious longsword.")

    def test_carmor_tags_and_wear(self):
        """Armor created with carmor gets tags and can be worn."""

        self.char1.execute_cmd("carmor head head 1 basic")
        armor = next(
            (o for o in self.char1.contents if "head" in list(o.aliases.all())),
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

        self.char1.execute_cmd("cshield buckler 1 5 1 basic shield")
        shield = next(
            (o for o in self.char1.contents if "buckler" in list(o.aliases.all())),
            None,
        )
        self.assertIsNotNone(shield)
        self.assertEqual(shield.db.block_rate, 5)
        self.assertTrue(shield.tags.has("shield", category="flag"))
        shield.wear(self.char1, True)
        self.assertTrue(shield.db.worn)
        self.assertTrue(shield.tags.has("shield", category="flag"))

        self.char1.attributes.add("_wielded", {"left": None, "right": None})
        weapon = create_object(
            "typeclasses.gear.MeleeWeapon", key="great", location=self.char1
        )
        weapon.tags.add("equipment", category="flag")
        weapon.tags.add("identified", category="flag")
        weapon.tags.add("twohanded", category="flag")
        self.assertIsNone(self.char1.at_wield(weapon))
        self.assertNotIn(weapon, self.char1.wielding)

    def test_cshield_with_modifiers(self):
        """Shield creation supports stat modifiers and description parsing."""

        self.char1.execute_cmd(
            "cshield kite 2 8 3 STR+1, Critical Resist+4 A sturdy kite shield."
        )
        shield = next(
            (
                o
                for o in self.char1.contents
                if "kite" in [al.lower() for al in o.aliases.all()]
            ),
            None,
        )
        self.assertIsNotNone(shield)
        self.assertEqual(shield.db.block_rate, 8)
        self.assertEqual(
            shield.db.modifiers,
            {"str": 1, "critical_resist": 4},
        )
        self.assertEqual(shield.db.stat_mods, {"str": 1, "critical_resist": 4})
        self.assertEqual(shield.db.desc, "A sturdy kite shield.")

    def test_cshield_block_and_magic_resist_mods(self):
        """cshield correctly parses block and magic resist modifiers."""

        self.char1.execute_cmd(
            "cshield buckler 2 5 1 Block Rate+5, Magic Resist+3 basic shield"
        )
        shield = next(
            (
                o
                for o in self.char1.contents
                if "buckler" in [al.lower() for al in o.aliases.all()]
            ),
            None,
        )
        self.assertIsNotNone(shield)
        self.assertEqual(
            shield.db.modifiers,
            {"block_rate": 5, "magic_resist": 3},
        )

    def test_cring_and_ctrinket_wear_and_display(self):
        """Rings and trinkets created by builders can be worn and show in equipment."""

        self.char1.execute_cmd("cring ruby")
        ring = next(
            (o for o in self.char1.contents if "ruby" in list(o.aliases.all())), None
        )
        self.assertIsNotNone(ring)
        ring.wear(self.char1, True)
        self.assertTrue(ring.db.worn)

        self.char1.msg.reset_mock()
        self.char1.execute_cmd("equipment")
        out = self.char1.msg.call_args[0][0]
        self.assertIn("Ring1", out)
        self.assertIn("ruby", out.lower())

        self.char1.execute_cmd("ctrinket charm")
        trinket = next(
            (o for o in self.char1.contents if "charm" in list(o.aliases.all())), None
        )
        self.assertIsNotNone(trinket)
        self.assertEqual(trinket.db.clothing_type, "trinket")
        self.assertTrue(trinket.tags.has("trinket", category="slot"))
        trinket.wear(self.char1, True)
        self.assertTrue(trinket.db.worn)

        self.char1.msg.reset_mock()
        self.char1.execute_cmd("equipment")
        out = self.char1.msg.call_args[0][0]
        self.assertIn("Trinket", out)
        self.assertIn("charm", out.lower())

    def test_carmor_with_modifiers(self):
        self.char1.execute_cmd("carmor head head 1 STR+1, Dex+2 A sturdy head.")
        armor = next(
            (
                o
                for o in self.char1.contents
                if "head" in [al.lower() for al in o.aliases.all()]
            ),
            None,
        )
        self.assertIsNotNone(armor)
        self.assertEqual(armor.db.stat_mods, {"str": 1, "dex": 2})
        self.assertEqual(armor.db.desc, "A sturdy head.")

    def test_ctool_with_modifiers(self):
        self.char1.execute_cmd(
            "ctool hammer smith 3 STR+2, Crafting Bonus+1 Heavy hammer."
        )
        tool = next((o for o in self.char1.contents if "hammer" in o.key.lower()), None)
        self.assertIsNotNone(tool)
        self.assertEqual(tool.db.weight, 3)
        self.assertEqual(tool.db.stat_mods, {"str": 2, "crafting_bonus": 1})
        self.assertEqual(tool.db.desc, "Heavy hammer.")

    def test_cring_with_modifiers(self):
        self.char1.execute_cmd("cring ruby ring2 1 STR+1, Luck+2 A jeweled ring.")
        ring = next(
            (
                o
                for o in self.char1.contents
                if "ruby" in [al.lower() for al in o.aliases.all()]
            ),
            None,
        )
        self.assertIsNotNone(ring)
        self.assertEqual(ring.db.stat_mods, {"str": 1, "luck": 2})
        self.assertEqual(ring.db.desc, "A jeweled ring.")

    def test_ctrinket_with_modifiers(self):
        self.char1.execute_cmd(
            "ctrinket charm 1 Wis+2, Stealth+3 A lucky charm."
        )
        trinket = next(
            (
                o
                for o in self.char1.contents
                if "charm" in [al.lower() for al in o.aliases.all()]
            ),
            None,
        )
        self.assertIsNotNone(trinket)
        self.assertEqual(trinket.db.clothing_type, "trinket")
        self.assertTrue(trinket.tags.has("trinket", category="slot"))
        self.assertEqual(trinket.db.stat_mods, {"wis": 2, "stealth": 3})
        self.assertEqual(trinket.db.desc, "A lucky charm.")

    def test_cgear_with_modifiers(self):
        self.char1.execute_cmd(
            "cgear typeclasses.objects.Object token accessory 1 1 STR+1, CON+2 A special token."
        )
        gear = next(
            (
                o
                for o in self.char1.contents
                if "token" in [al.lower() for al in o.aliases.all()]
            ),
            None,
        )
        self.assertIsNotNone(gear)
        self.assertEqual(gear.db.stat_mods, {"str": 1, "con": 2})
        self.assertEqual(gear.db.desc, "A special token.")

    def test_creation_commands_strip_quotes(self):
        self.char1.execute_cmd('cweapon "long sword" mainhand 3 1 sharp blade')
        weapon = next((o for o in self.char1.contents if o.key == "Long sword"), None)
        self.assertIsNotNone(weapon)

        self.char1.execute_cmd('cshield "kite shield" 2 5 1 sturdy')
        shield = next((o for o in self.char1.contents if o.key == "kite shield"), None)
        self.assertIsNotNone(shield)

        self.char1.execute_cmd('carmor "iron head" head 1 basic')
        armor = next((o for o in self.char1.contents if o.key == "iron head"), None)
        self.assertIsNotNone(armor)

        self.char1.execute_cmd('ctool "rock hammer" smith 2 heavy')
        tool = next((o for o in self.char1.contents if o.key == "rock hammer"), None)
        self.assertIsNotNone(tool)

        self.char1.execute_cmd('cring "ruby ring" ring2 1 shiny')
        ring = next((o for o in self.char1.contents if o.key == "ruby ring"), None)
        self.assertIsNotNone(ring)

        self.char1.execute_cmd('ctrinket "lucky charm" 1 shiny')
        trinket = next((o for o in self.char1.contents if o.key == "lucky charm"), None)
        self.assertIsNotNone(trinket)
        self.assertEqual(trinket.db.clothing_type, "trinket")
        self.assertTrue(trinket.tags.has("trinket", category="slot"))

        self.char1.execute_cmd('cgear typeclasses.objects.Object "mysterious orb" accessory 1 1 odd')
        gear = next((o for o in self.char1.contents if o.key == "mysterious orb"), None)
        self.assertIsNotNone(gear)

        self.char1.execute_cmd('ocreate "strange box" 1')
        obj = next((o for o in self.char1.contents if o.key == "strange box"), None)
        self.assertIsNotNone(obj)

    def test_cweapon_color_name_capitalization(self):
        self.char1.execute_cmd('cweapon "|BBigger Ass Sword|n" mainhand 3 1 sharp')
        weapon = next((o for o in self.char1.contents if strip_ansi(o.key) == "Bigger Ass Sword"), None)
        self.assertIsNotNone(weapon)
        self.assertEqual(weapon.key, "|BBigger Ass Sword|n")

    def test_peace_on_fresh_combat(self):
        """Peace should immediately end a newly started fight."""

        from commands.combat import CombatCmdSet
        from commands.admin import CmdPeace

        self.char1.cmdset.add_default(CombatCmdSet)
        self.char2.cmdset.add_default(CombatCmdSet)

        # avoid running the full combat logic
        self.char1.attack = MagicMock()

        # start combat via attack command
        self.char1.execute_cmd(f"attack {self.char2.key}")

        self.assertTrue(self.char1.in_combat)

        cmd = CmdPeace()
        cmd.caller = self.char1
        cmd.func()

        from combat.round_manager import CombatRoundManager
        self.assertFalse(CombatRoundManager.get().combats)

    def test_peace_after_victory(self):
        """Peace should handle the combat script being deleted already."""

        from combat.round_manager import CombatRoundManager

        manager = CombatRoundManager.get()
        instance = manager.start_combat([self.char1, self.char2])

        # defeat the opponent
        self.char2.tags.add("dead", category="status")
        instance.engine.process_round()
        manager._tick()

        # combat instance should now be deleted
        self.assertFalse(manager.combats)

        self.char1.msg.reset_mock()
        self.char1.execute_cmd("peace")
        self.char1.msg.assert_called_with("There is no fighting here.")

    def test_peace_after_victory_from_active_combat(self):
        """Calling peace after combat ends should report no fighting."""

        from commands.combat import CombatCmdSet

        # allow starting combat via command
        self.char1.cmdset.add_default(CombatCmdSet)
        self.char2.cmdset.add_default(CombatCmdSet)

        self.char1.attack = MagicMock()

        # start combat
        self.char1.execute_cmd(f"attack {self.char2.key}")
        from combat.round_manager import CombatRoundManager
        manager = CombatRoundManager.get()
        instance = manager.get_combatant_combat(self.char1)

        # defeat the opponent so combat ends
        self.char2.tags.add("dead", category="status")
        instance.engine.process_round()

        # ensure instance is removed
        manager._tick()
        self.assertFalse(manager.combats)

        self.char1.msg.reset_mock()
        self.char1.execute_cmd("peace")
        self.char1.msg.assert_called_with("There is no fighting here.")

    def test_peace_after_npc_initiated_combat(self):
        """NPC-initiated combat should be stopped cleanly by peace."""

        from typeclasses.npcs import BaseNPC
        from commands.admin import CmdPeace
        from evennia.utils import create

        npc = create.create_object(BaseNPC, key="mob", location=self.room1)
        npc.attack = MagicMock()

        npc.enter_combat(self.char1)

        self.assertTrue(npc.in_combat)
        self.assertTrue(self.char1.in_combat)

        cmd = CmdPeace()
        cmd.caller = self.char1
        cmd.func()

        from combat.round_manager import CombatRoundManager
        self.assertFalse(CombatRoundManager.get().combats)

    def test_peace_clears_room_combat_tags(self):
        """After using peace, room occupants should no longer show fighting tags."""

        from commands.combat import CombatCmdSet
        from commands.admin import CmdPeace

        self.char1.cmdset.add_default(CombatCmdSet)
        self.char2.cmdset.add_default(CombatCmdSet)

        # mock attack to avoid full combat loop
        self.char1.attack = MagicMock()

        # start combat and verify tag appears
        self.char1.execute_cmd(f"attack {self.char2.key}")
        out = self.room1.return_appearance(self.char1)
        self.assertIn(f"[fighting {self.char2.get_display_name(self.char1)}]", out)

        cmd = CmdPeace()
        cmd.caller = self.char1
        cmd.func()

        # combat ended - tags should be gone
        out = self.room1.return_appearance(self.char1)
        self.assertNotIn("[fighting", out)

    def test_force_mob_report(self):
        from commands.admin import CmdForceMobReport

        cmd = CmdForceMobReport()
        cmd.caller = self.char1
        cmd.args = self.char2.key
        self.room1.msg_contents = MagicMock()
        cmd.func()
        output = self.room1.msg_contents.call_args[0][0]
        self.assertIn(self.char2.key, output)
        self.assertIn("HP", output)

