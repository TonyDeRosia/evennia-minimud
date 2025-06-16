import unittest
from unittest.mock import patch

from evennia.utils.test_resources import EvenniaTest
from django.test import override_settings
from combat import combat_utils
from typeclasses.gear import BareHand
from world import stats
from world.recipes.base import SkillRecipe
from world.guilds import Guild, auto_promote, ADVENTURERS_GUILD_RANKS


class DummyRecipe(SkillRecipe):
    key = "dummy"
    skill = ("smithing", 10)


@override_settings(DEFAULT_HOME=None)
class TestExtendedStats(EvenniaTest):
    def setUp(self):
        super().setUp()
        stats.apply_stats(self.char1)
        stats.apply_stats(self.char2)

    def test_evasion_blocks_attack(self):
        self.char2.traits.evasion.base = 100
        with patch("combat.combat_utils.random.randint", return_value=1), patch(
            "world.system.stat_manager.check_hit", return_value=True
        ):
            before = self.char2.traits.health.current
            BareHand().at_attack(self.char1, self.char2)
            self.assertEqual(self.char2.traits.health.current, before)

    def test_attack_power_increases_damage(self):
        self.char1.traits.attack_power.base = 100
        self.char2.traits.armor.base = 0
        with patch("combat.combat_utils.random.randint", return_value=100), patch(
            "world.system.stat_manager.check_hit", return_value=True
        ), patch("typeclasses.gear.roll_dice_string", return_value=2):
            before = self.char2.traits.health.current
            BareHand().at_attack(self.char1, self.char2)
            self.assertLess(self.char2.traits.health.current, before - 2)

    def test_piercing_reduces_armor(self):
        self.char1.traits.piercing.base = 5
        self.char2.db.armor = 10
        dmg = self.char2.at_damage(self.char1, 20)
        self.assertEqual(dmg, 15)

    def test_spell_pen_and_resist(self):
        self.char1.traits.spell_penetration.base = 5
        self.char2.traits.magic_resist.base = 10
        dmg = self.char2.at_damage(self.char1, 20, damage_type="fire")
        self.assertEqual(dmg, 15)

    def test_lifesteal_and_leech(self):
        self.char1.traits.lifesteal.base = 50
        self.char1.traits.leech.base = 50
        self.char1.traits.health.current = 50
        self.char1.traits.mana.current = 50
        before_hp = self.char1.traits.health.current
        before_mp = self.char1.traits.mana.current
        combat_utils.apply_lifesteal(self.char1, 20)
        self.assertGreater(self.char1.traits.health.current, before_hp)
        self.assertGreater(self.char1.traits.mana.current, before_mp)

    def test_cooldown_reduction(self):
        from world.system import state_manager

        self.char1.traits.cooldown_reduction.base = 50
        state_manager.add_cooldown(self.char1, "test", 10)
        self.assertLess(self.char1.cooldowns.time_left("test", use_int=True), 10)


    def test_threat_increases_aggro(self):
        from combat.engine import CombatEngine

        self.char1.traits.threat.base = 5
        engine = CombatEngine([self.char1, self.char2], round_time=0)
        engine.track_aggro(self.char2, self.char1)
        self.assertGreater(engine.aggro[self.char2][self.char1], 1)

    def test_craft_bonus_affects_roll(self):
        recipe = DummyRecipe(crafter=self.char1)
        self.char1.traits.add("smithing", "Smith", trait_type="counter")
        self.char1.traits.smithing.base = 20
        self.char1.traits.craft_bonus.base = 5
        with patch("world.recipes.base.randint", return_value=1) as mock_rand:
            recipe.craft()
            mock_rand.assert_called_with(0, 15)



if __name__ == "__main__":
    unittest.main()
