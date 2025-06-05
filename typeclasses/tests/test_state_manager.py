from evennia.utils.test_resources import EvenniaTest
from world.system import state_manager


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
