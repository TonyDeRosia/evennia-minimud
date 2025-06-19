from unittest.mock import MagicMock, patch

from utils import normalize_slot

from evennia import create_object
from evennia.utils.test_resources import EvenniaTest


class TestObjectCreation(EvenniaTest):
    def test_default_weight_on_creation(self):
        obj = create_object("typeclasses.objects.Object", key="widget")
        self.assertEqual(obj.db.weight, 0)

    def test_weight_not_overwritten(self):
        obj = create_object("typeclasses.objects.Object", key="stone")
        obj.db.weight = 5
        obj.at_object_creation()
        self.assertEqual(obj.db.weight, 5)


class TestObjectFlags(EvenniaTest):
    def test_stationary_blocks_move(self):
        obj = create_object("typeclasses.objects.Object", key="rock")
        obj.tags.add("stationary", category="flag")
        mover = self.char1
        mover.msg = MagicMock()
        result = obj.at_pre_move(self.room2, caller=mover)
        self.assertFalse(result)
        mover.msg.assert_called_with(f"{obj.get_display_name(mover)} refuses to budge.")

    @patch("typeclasses.objects.ContribClothing.wear")
    def test_wear_requires_flags(self, mock_wear):
        item = create_object("typeclasses.objects.ClothingObject", key="cloak", location=self.char1)
        self.char1.msg = MagicMock()

        # Missing equipment flag
        item.tags.add("identified", category="flag")
        item.wear(self.char1, "wear")
        self.char1.msg.assert_called_with(f"{item.get_display_name(self.char1)} can't be worn.")
        mock_wear.assert_not_called()
        self.char1.msg.reset_mock()

        # Missing identified flag
        item.tags.add("equipment", category="flag")
        item.tags.remove("identified", category="flag")
        item.wear(self.char1, "wear")
        self.char1.msg.assert_called_with(f"You don't know how to use {item.get_display_name(self.char1)}.")
        mock_wear.assert_not_called()
        self.char1.msg.reset_mock()

        # Has both flags
        item.tags.add("identified", category="flag")
        item.wear(self.char1, "wear")
        mock_wear.assert_called()

    def test_wear_replaces_existing(self):
        first = create_object(
            "typeclasses.objects.ClothingObject",
            key="hat1",
            location=self.char1,
        )
        first.tags.add("equipment", category="flag")
        first.tags.add("identified", category="flag")
        first.tags.add("head", category="slot")

        second = create_object(
            "typeclasses.objects.ClothingObject",
            key="hat2",
            location=self.char1,
        )
        second.tags.add("equipment", category="flag")
        second.tags.add("identified", category="flag")
        second.tags.add("head", category="slot")

        first.wear(self.char1, "wear")
        self.assertTrue(first.db.worn)
        slot = normalize_slot("head")
        self.assertEqual(self.char1.db.equipment.get(slot), first)

        second.wear(self.char1, "wear")
        self.assertTrue(second.db.worn)
        self.assertFalse(first.db.worn)
        self.assertEqual(first.location, self.char1)
        self.assertEqual(self.char1.db.equipment.get(slot), second)

    def test_wear_adds_canonical_slot_tag(self):
        item = create_object(
            "typeclasses.objects.ClothingObject",
            key="ring",
            location=self.char1,
        )
        item.tags.add("equipment", category="flag")
        item.tags.add("identified", category="flag")
        item.tags.add("ring", category="slot")

        item.wear(self.char1, True)
        self.assertTrue(item.tags.has("ring1", category="slot"))


class TestInspectFlags(EvenniaTest):
    def test_inspect_shows_flags(self):
        obj = self.obj1
        obj.db.desc = "A shiny object."
        obj.db.identified = True
        obj.tags.add("equipment", category="flag")
        obj.tags.add("rare", category="flag")
        self.char1.msg = MagicMock()
        self.char1.execute_cmd(f"inspect {obj.key}")
        out = self.char1.msg.call_args[0][0]
        self.assertIn("Flags: equipment, rare", out)


class TestMeleeWeaponUtility(EvenniaTest):
    def test_is_twohanded_attribute(self):
        weapon = create_object(
            "typeclasses.gear.MeleeWeapon",
            key="great",
            location=self.char1,
            nohome=True,
        )
        weapon.db.twohanded = True
        self.assertTrue(weapon.is_twohanded())

    def test_is_twohanded_flag_tag(self):
        weapon = create_object(
            "typeclasses.gear.MeleeWeapon",
            key="axe",
            location=self.char1,
            nohome=True,
        )
        weapon.tags.add("twohanded", category="flag")
        self.assertTrue(weapon.is_twohanded())

    def test_is_twohanded_wielded_tag(self):
        weapon = create_object(
            "typeclasses.gear.MeleeWeapon",
            key="spear",
            location=self.char1,
            nohome=True,
        )
        weapon.tags.add("two_handed", category="wielded")
        self.assertTrue(weapon.is_twohanded())

    def test_is_twohanded_false(self):
        weapon = create_object(
            "typeclasses.gear.MeleeWeapon",
            key="sword",
            location=self.char1,
            nohome=True,
        )
        self.assertFalse(weapon.is_twohanded())


class TestWearableContainer(EvenniaTest):
    def test_wear_sets_worn_by_and_remove_clears(self):
        bag = create_object(
            "typeclasses.gear.WearableContainer", key="bag", location=self.char1
        )
        bag.tags.add("equipment", category="flag")
        bag.tags.add("identified", category="flag")
        bag.wear(self.char1, "wear")
        self.assertIs(bag.db.worn_by, self.char1)
        bag.remove(self.char1)
        self.assertIsNone(bag.db.worn_by)

    def test_capacity_blocks_extra_items(self):
        bag = create_object(
            "typeclasses.gear.WearableContainer", key="bag", location=self.char1
        )
        bag.capacity = 1
        bag.tags.add("equipment", category="flag")
        bag.tags.add("identified", category="flag")
        bag.wear(self.char1, "wear")

        obj1 = create_object("typeclasses.objects.Object", key="rock1")
        obj2 = create_object("typeclasses.objects.Object", key="rock2")

        self.assertTrue(bag.at_pre_put_in(self.char1, obj1))
        obj1.move_to(bag, quiet=True)
        self.assertFalse(bag.at_pre_put_in(self.char1, obj2))


class TestRoomHeaders(EvenniaTest):
    def test_room_header_displays_meta(self):
        from typeclasses.rooms import Room

        room = create_object(Room, key="testroom")
        room.set_area("Town")
        room.set_room_id(5)
        header = room.get_display_header(self.char1)
        self.assertIn("Town", header)
        self.assertIn("#5", header)

    def test_xygrid_header_shows_coordinates(self):
        from typeclasses.rooms import XYGridRoom

        room, errors = XYGridRoom.create(key="xy", xyz=(2, 3, "zone"))
        self.assertFalse(errors)
        header = room.get_display_header(self.char1)
        self.assertIn("(2, 3, zone)", header)


class TestRoomDisplayName(EvenniaTest):
    def test_display_name_builder_shows_vnum(self):
        from typeclasses.rooms import Room

        room = create_object(Room, key="field")
        room.set_area("verdant_overgrowth", 200004)
        self.char1.permissions.add("Builder")

        name = room.get_display_name(self.char1)
        self.assertEqual(name, "field (verdant_overgrowth) - 200004")

    def test_display_name_player_no_vnum(self):
        from typeclasses.rooms import Room

        room = create_object(Room, key="field")
        room.set_area("verdant_overgrowth", 200004)

        name = room.get_display_name(self.char1)
        self.assertEqual(name, "field")


class TestRoomAppearanceMetadata(EvenniaTest):
    def test_builder_sees_area_and_vnum(self):
        from typeclasses.rooms import Room

        room = create_object(Room, key="square")
        room.set_area("Midgard", 200054)
        self.char1.permissions.add("Builder")

        out = room.return_appearance(self.char1)
        self.assertIn("Midgard [vnum: 200054]", out)

    def test_player_hides_area_and_vnum(self):
        from typeclasses.rooms import Room

        room = create_object(Room, key="square")
        room.set_area("Midgard", 200054)

        out = room.return_appearance(self.char1)
        self.assertNotIn("vnum: 200054", out)


class TestMeleeWeaponAtAttack(EvenniaTest):
    def test_damage_dice_only(self):
        weapon = create_object(
            "typeclasses.gear.MeleeWeapon", key="sword", location=self.char1
        )
        weapon.tags.add("equipment", category="flag")
        weapon.tags.add("identified", category="flag")
        weapon.db.damage_dice = "1d4"

        self.char1.at_emote = MagicMock()
        with patch("world.system.stat_manager.check_hit", return_value=False), patch(
            "combat.combat_utils.roll_damage", return_value=2
        ) as mock_roll:
            weapon.at_attack(self.char1, self.char2)
            mock_roll.assert_called_with((1, 4))

    def test_damage_mapping_with_dice_strings(self):
        weapon = create_object(
            "typeclasses.gear.MeleeWeapon", key="sword", location=self.char1
        )
        weapon.tags.add("equipment", category="flag")
        weapon.tags.add("identified", category="flag")
        weapon.db.damage = {"slash": "1d4", "fire": "1d6"}

        self.char2.at_damage = MagicMock()
        self.char1.at_emote = MagicMock()
        with patch("world.system.stat_manager.check_hit", return_value=True), patch(
            "combat.combat_utils.roll_evade", return_value=False
        ), patch("combat.combat_utils.roll_parry", return_value=False), patch(
            "combat.combat_utils.roll_block", return_value=False
        ), patch(
            "world.system.stat_manager.roll_crit", return_value=False
        ), patch(
            "combat.combat_utils.apply_attack_power", side_effect=lambda w, d: d
        ), patch(
            "combat.combat_utils.apply_lifesteal"
        ), patch(
            "utils.dice.roll_dice_string", side_effect=[2, 3]
        ) as mock_roll:
            weapon.at_attack(self.char1, self.char2)
            mock_roll.assert_any_call("1d4")
            mock_roll.assert_any_call("1d6")
        self.char2.at_damage.assert_called_with(self.char1, 5, "slash", critical=False)

