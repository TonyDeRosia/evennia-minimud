from evennia.utils.test_resources import EvenniaTest
from django.test import override_settings
from world.system import state_manager


@override_settings(DEFAULT_HOME=None)
class TestStateManager(EvenniaTest):
    def test_temp_stat_bonus_and_expiry(self):
        char = self.char1
        state_manager.add_temp_stat_bonus(char, "STR", 5, 2)
        base = char.traits.STR.value
        self.assertEqual(
            state_manager.get_effective_stat(char, "STR"), base + 5
        )
        state_manager.tick_all()
        self.assertEqual(
            state_manager.get_effective_stat(char, "STR"), base + 5
        )
        state_manager.tick_all()
        self.assertEqual(
            state_manager.get_effective_stat(char, "STR"), base
        )

    def test_status_effects(self):
        char = self.char1
        state_manager.add_status_effect(char, "stunned", 1)
        self.assertTrue(char.tags.has("stunned", category="status"))
        state_manager.tick_all()
        self.assertFalse(char.tags.has("stunned", category="status"))

    def test_cooldown_api(self):
        char = self.char1
        state_manager.add_cooldown(char, "test", 2)
        self.assertTrue(char.cooldowns.time_left("test", use_int=True))
        state_manager.remove_cooldown(char, "test")
        self.assertEqual(char.cooldowns.time_left("test", use_int=True), 0)

    def test_temp_bonus_effect_key_preserved(self):
        char = self.char1
        state_manager.add_temp_stat_bonus(char, "STR", 5, 2, effect_key="speed")
        entry = char.db.temp_bonuses["STR"][0]
        self.assertEqual(entry["key"], "speed")
        state_manager.tick_character(char)
        entry_after = char.db.temp_bonuses["STR"][0]
        self.assertEqual(entry_after["key"], "speed")

    def test_sated_and_hungry_effect(self):
        char = self.char1
        char.db.sated = 1
        hp = char.traits.health.current
        mp = char.traits.mana.current
        sp = char.traits.stamina.current
        state_manager.tick_character(char)
        self.assertEqual(char.db.sated, 0)
        self.assertTrue(char.tags.has("hungry_thirsty", category="status"))
        loss = int(round(char.traits.health.max * 0.05))
        self.assertEqual(char.traits.health.current, hp - loss)
        self.assertEqual(char.traits.mana.current, mp - loss)
        self.assertEqual(char.traits.stamina.current, sp - loss)

    def test_hunger_ticks_reduce_sated(self):
        char = self.char1
        char.db.sated = 2
        hp = char.traits.health.current
        mp = char.traits.mana.current
        sp = char.traits.stamina.current
        state_manager.tick_character(char)
        self.assertEqual(char.db.sated, 1)
        self.assertEqual(char.traits.health.current, hp)
        state_manager.tick_character(char)
        self.assertEqual(char.db.sated, 0)
        self.assertTrue(char.tags.has("hungry_thirsty", category="status"))
        loss = int(round(char.traits.health.max * 0.05))
        self.assertEqual(char.traits.health.current, hp - loss)
        self.assertEqual(char.traits.mana.current, mp - loss)
        self.assertEqual(char.traits.stamina.current, sp - loss)

    def test_hunger_cap(self):
        char = self.char1
        char.db.sated = 150
        state_manager.tick_character(char)
        self.assertLessEqual(char.db.sated, state_manager.MAX_SATED)

    def test_hunger_ignored_at_max_level(self):
        char = self.char1
        char.db.level = state_manager.MAX_LEVEL
        char.db.sated = 1
        hp = char.traits.health.current
        state_manager.tick_character(char)
        self.assertEqual(char.db.sated, 1)
        self.assertFalse(char.tags.has("hungry_thirsty", category="status"))
        self.assertEqual(char.traits.health.current, hp)

    def test_hunger_drains_all_resources(self):
        char = self.char1
        char.db.sated = 0
        hp = char.traits.health.current
        mp = char.traits.mana.current
        sp = char.traits.stamina.current
        state_manager.tick_character(char)
        loss = int(round(char.traits.health.max * 0.05))
        self.assertEqual(char.traits.health.current, hp - loss)
        self.assertEqual(char.traits.mana.current, mp - loss)
        self.assertEqual(char.traits.stamina.current, sp - loss)

    def test_apply_regen_uses_derived_stats(self):
        char = self.char1
        for key in ("health", "mana", "stamina"):
            trait = char.traits.get(key)
            trait.current = trait.max // 2
        char.db.derived_stats = {
            "health_regen": 2,
            "mana_regen": 3,
            "stamina_regen": 4,
        }

        healed = state_manager.apply_regen(char)

        expected = {"health": 2, "mana": 3, "stamina": 4}
        self.assertEqual(healed, expected)
        for key, regen in expected.items():
            trait = char.traits.get(key)
            self.assertEqual(trait.current, trait.max // 2 + regen)

    def test_apply_regen_scales_with_status(self):
        char = self.char1
        for key in ("health", "mana", "stamina"):
            trait = char.traits.get(key)
            trait.current = trait.max // 2
        char.db.derived_stats = {
            "health_regen": 2,
            "mana_regen": 3,
            "stamina_regen": 4,
        }
        char.tags.add("sitting", category="status")

        healed = state_manager.apply_regen(char)

        expected = {"health": 4, "mana": 6, "stamina": 8}
        self.assertEqual(healed, expected)
        for key, regen in expected.items():
            trait = char.traits.get(key)
            self.assertEqual(trait.current, trait.max // 2 + regen)

    def test_apply_regen_rest_area_bonus(self):
        char = self.char1
        for key in ("health", "mana", "stamina"):
            trait = char.traits.get(key)
            trait.current = trait.max // 2
        char.db.derived_stats = {
            "health_regen": 2,
            "mana_regen": 3,
            "stamina_regen": 4,
        }
        char.tags.add("sitting", category="status")
        char.location.tags.add("rest_area", category="room_flag")

        healed = state_manager.apply_regen(char)

        expected = {"health": 6, "mana": 9, "stamina": 12}
        self.assertEqual(healed, expected)
        for key, regen in expected.items():
            trait = char.traits.get(key)
            self.assertEqual(trait.current, trait.max // 2 + regen)

