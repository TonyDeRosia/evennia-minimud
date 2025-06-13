from evennia.utils.test_resources import EvenniaTest
from evennia.utils import create
from django.test import override_settings
from world.system import stat_manager, state_manager
from world import stats


class TestStatManager(EvenniaTest):
    def setUp(self):
        super().setUp()
        stats.apply_stats(self.char1)

    def test_refresh_stats_race_class(self):
        char = self.char1
        char.db.race = "Elf"
        char.db.charclass = "Wizard"
        stat_manager.refresh_stats(char)
        self.assertEqual(char.traits.DEX.base, 7)
        self.assertEqual(char.traits.INT.base, 9)
        self.assertEqual(char.traits.STR.base, 4)
        self.assertEqual(char.traits.CON.base, 4)
        self.assertEqual(char.traits.WIS.base, 6)

    def test_effective_stat_with_temp_bonus(self):
        char = self.char1
        stat_manager.refresh_stats(char)
        base = char.traits.STR.value
        state_manager.add_temp_stat_bonus(char, "STR", 3, 1)
        self.assertEqual(stat_manager.get_effective_stat(char, "STR"), base + 3)

    def test_display_stat_block(self):
        char = self.char1
        stat_manager.refresh_stats(char)
        text = stat_manager.display_stat_block(char)
        self.assertIn("╔", text)
        self.assertIn("╚", text)
        self.assertIn("STR", text)
        self.assertIn("HP", text)

    def test_derived_stats_increase_with_primary(self):
        char = self.char1
        stat_manager.refresh_stats(char)

        base_attack = char.db.derived_stats.get("attack_power")
        char.traits.STR.base += 5
        stat_manager.refresh_stats(char)
        self.assertGreater(char.db.derived_stats.get("attack_power"), base_attack)

        base_regen = char.db.derived_stats.get("mana_regen")
        char.traits.WIS.base += 3
        stat_manager.refresh_stats(char)
        self.assertGreater(char.db.derived_stats.get("mana_regen"), base_regen)

        base_stealth = char.db.derived_stats.get("stealth")
        char.traits.DEX.base += 2
        stat_manager.refresh_stats(char)
        self.assertGreater(char.db.derived_stats.get("stealth"), base_stealth)

    def test_refresh_stats_handles_missing_base_stats(self):
        char = self.char1
        char.db.base_primary_stats = None
        stat_manager.refresh_stats(char)
        self.assertIsInstance(char.db.base_primary_stats, dict)
        for key in stats.CORE_STAT_KEYS:
            self.assertIn(key, char.db.base_primary_stats)

    def test_initial_refresh_with_equipped_item(self):
        """Bonuses shouldn't invert stats when cached for the first time."""
        char = self.char1
        char.db.base_primary_stats = None

        item = create.create_object(
            "typeclasses.objects.ClothingObject",
            key="ring",
            location=char,
        )
        item.tags.add("equipment", category="flag")
        item.tags.add("identified", category="flag")
        item.db.stat_mods = {"STR": 15}
        item.wear(char, True)

        # after equipping, STR base should remain positive
        self.assertEqual(char.db.base_primary_stats.get("STR"), 5)
        self.assertEqual(char.traits.STR.base, 20)

    def test_stat_overrides(self):
        char = self.char1
        char.db.stat_overrides = {"attack_power": 123}
        stat_manager.refresh_stats(char)
        self.assertEqual(char.db.derived_stats.get("attack_power"), 123)

    def test_active_effect_modifiers(self):
        char = self.char1
        stat_manager.refresh_stats(char)
        base = char.traits.STR.base
        state_manager.add_effect(char, "STR", 2)
        self.assertEqual(char.traits.STR.base, base + 5)
        self.assertEqual(stat_manager.get_effective_stat(char, "STR"), base + 5)
        state_manager.tick_character(char)
        state_manager.tick_character(char)
        self.assertEqual(char.traits.STR.base, base)

    def test_debuff_modifiers(self):
        char = self.char1
        stat_manager.refresh_stats(char)
        base = char.traits.DEX.base
        state_manager.add_effect(char, "stunned", 1)
        self.assertEqual(char.traits.DEX.base, base - 5)
        state_manager.tick_character(char)
        self.assertEqual(char.traits.DEX.base, base)

    def test_gear_buffs_apply(self):
        char = self.char1
        stat_manager.refresh_stats(char)
        base_hp = char.db.derived_stats.get("HP")
        item = create.create_object(
            "typeclasses.objects.ClothingObject",
            key="neck",
            location=char,
        )
        item.tags.add("equipment", category="flag")
        item.tags.add("identified", category="flag")
        item.db.buffs = {"HP": 100}
        item.wear(char, True)
        stat_manager.refresh_stats(char)
        self.assertEqual(char.db.equip_bonuses.get("HP"), 100)
        self.assertEqual(char.db.derived_stats.get("HP"), base_hp + 100)

    def test_equip_bonus_removed(self):
        char = self.char1
        stat_manager.refresh_stats(char)
        item = create.create_object(
            "typeclasses.objects.ClothingObject",
            key="ring",
            location=char,
        )
        item.tags.add("equipment", category="flag")
        item.tags.add("identified", category="flag")
        item.db.modifiers = {"STR": 2}
        item.wear(char, True)
        stat_manager.refresh_stats(char)
        self.assertEqual(char.db.equip_bonuses.get("STR"), 2)
        item.remove(char, True)
        stat_manager.refresh_stats(char)
        self.assertFalse(char.db.equip_bonuses)

    def test_lowercase_item_modifiers(self):
        char = self.char1
        stat_manager.refresh_stats(char)
        base_str = char.traits.STR.base
        base_per = char.db.derived_stats.get("perception")

        item = create.create_object(
            "typeclasses.objects.ClothingObject",
            key="bauble",
            location=char,
        )
        item.tags.add("equipment", category="flag")
        item.tags.add("identified", category="flag")
        item.db.stat_mods = {"str": 2, "per": 100}
        item.wear(char, True)
        stat_manager.refresh_stats(char)

        self.assertEqual(char.db.equip_bonuses.get("STR"), 2)
        self.assertEqual(char.db.equip_bonuses.get("perception"), 100)
        self.assertEqual(char.traits.STR.base, base_str + 2)
        self.assertEqual(char.db.derived_stats.get("perception"), base_per + 100)

    def test_hp_and_atk_alias_modifiers(self):
        char = self.char1
        stat_manager.refresh_stats(char)
        base_hp = char.db.derived_stats.get("HP")
        base_atk = char.db.derived_stats.get("ATK")

        item = create.create_object(
            "typeclasses.objects.ClothingObject",
            key="charm",
            location=char,
        )
        item.tags.add("equipment", category="flag")
        item.tags.add("identified", category="flag")
        item.db.stat_mods = {"hp": 25, "atk": 3}
        item.wear(char, True)
        stat_manager.refresh_stats(char)

        self.assertEqual(char.db.equip_bonuses.get("HP"), 25)
        self.assertEqual(char.db.equip_bonuses.get("ATK"), 3)
        self.assertEqual(char.db.derived_stats.get("HP"), base_hp + 25)
        self.assertEqual(char.db.derived_stats.get("ATK"), base_atk + 3)

    @override_settings(DEFAULT_HOME=None)
    def test_armor_increases_with_gear(self):
        char = self.char1
        stat_manager.refresh_stats(char)
        base_armor = char.traits.armor.base
        item = create.create_object(
            "typeclasses.objects.ClothingObject",
            key="helmet",
            location=char,
            nohome=True,
        )
        item.tags.add("equipment", category="flag")
        item.tags.add("identified", category="flag")
        item.db.armor = 5
        item.wear(char, True)
        self.assertEqual(char.traits.armor.base, base_armor + 5)
        item.remove(char, True)
        self.assertEqual(char.traits.armor.base, base_armor)


@override_settings(DEFAULT_HOME=None)
class TestBonusPersistence(EvenniaTest):
    def setUp(self):
        super().setUp()
        stats.apply_stats(self.char1)

    def _equip_item(self):
        item = create.create_object(
            "typeclasses.objects.ClothingObject",
            key="amulet",
            location=self.char1,
        )
        item.tags.add("equipment", category="flag")
        item.tags.add("identified", category="flag")
        item.tags.add("amulet", category="slot")
        item.db.stat_mods = {"STR": 2, "HP": 10}
        item.wear(self.char1, True)
        stat_manager.refresh_stats(self.char1)
        return item

    def test_score_does_not_stack_bonuses(self):
        self._equip_item()
        base_str = self.char1.traits.STR.base
        base_hp = self.char1.db.derived_stats.get("HP")
        self.char1.execute_cmd("score")
        self.char1.execute_cmd("score")
        self.assertEqual(self.char1.traits.STR.base, base_str)
        self.assertEqual(self.char1.db.derived_stats.get("HP"), base_hp)

    def test_look_does_not_stack_bonuses(self):
        self._equip_item()
        base_str = self.char1.traits.STR.base
        base_hp = self.char1.db.derived_stats.get("HP")
        self.char1.execute_cmd("look")
        self.char1.execute_cmd("look")
        self.assertEqual(self.char1.traits.STR.base, base_str)
        self.assertEqual(self.char1.db.derived_stats.get("HP"), base_hp)

    def test_equipment_reload_keeps_bonuses(self):
        item = self._equip_item()
        base_bonus = dict(self.char1.db.equip_bonuses)

        equip_data = dict(self.char1.db.equipment)
        self.char1.db.equip_bonuses = {}
        self.char1.db.equipment = equip_data

        stat_manager.recalculate_stats(self.char1)

        self.assertEqual(self.char1.db.equip_bonuses, base_bonus)

    def test_recalculate_does_not_stack(self):
        item = self._equip_item()
        base_str = self.char1.traits.STR.base

        stat_manager.recalculate_stats(self.char1)
        stat_manager.recalculate_stats(self.char1)

        self.assertEqual(self.char1.traits.STR.base, base_str)

    def test_remove_clears_slot_and_bonus(self):
        item = self._equip_item()
        item.remove(self.char1, True)
        stat_manager.refresh_stats(self.char1)

        self.assertFalse(self.char1.db.equipment.get("neck"))
        self.assertFalse(self.char1.db.equip_bonuses)

    def test_forced_move_clears_bonus(self):
        item = self._equip_item()
        # forcibly move the equipped item out of inventory
        item.location = self.room2
        stat_manager.refresh_stats(self.char1)

        self.assertFalse(self.char1.db.equip_bonuses)
        self.assertFalse(any(itm == item for itm in self.char1.db.equipment.values()))

    @override_settings(DEFAULT_HOME="#1")
    def test_delete_clears_bonus(self):
        item = self._equip_item()
        item.delete()
        stat_manager.refresh_stats(self.char1)

        self.assertFalse(self.char1.db.equip_bonuses)
        self.assertFalse(any(itm == item for itm in self.char1.db.equipment.values()))

    def test_effective_stat_handles_objects_without_traits(self):
        obj = create.create_object("typeclasses.objects.Object", key="rock")
        self.assertEqual(stat_manager.get_effective_stat(obj, "STR"), 0)
        self.assertEqual(state_manager.get_effective_stat(obj, "STR"), 0)
