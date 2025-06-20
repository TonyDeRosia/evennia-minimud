from unittest.mock import patch, MagicMock
from evennia.utils.test_resources import EvenniaTest
from combat.combat_skills import SKILL_CLASSES
from combat.spells import SPELLS

class TestSkillAndSpellUsage(EvenniaTest):
    def setUp(self):
        super().setUp()
        # ensure characters have sample spell known
        self.char1.db.spells = [SPELLS["fireball"]]
        self.char1.msg = MagicMock()

    def test_cast_spell_applies_cost_and_cooldown(self):
        mana_before = self.char1.traits.mana.current
        with patch("utils.hit_chance.calculate_hit_success", return_value=True):
            result = self.char1.cast_spell("fireball", target=self.char2)
        self.assertTrue(result)
        self.assertEqual(self.char1.traits.mana.current, mana_before - SPELLS["fireball"].mana_cost)
        self.assertTrue(self.char1.cooldowns.time_left("fireball", use_int=True))

    def test_use_skill_applies_cost_and_cooldown(self):
        skill_cls = SKILL_CLASSES["cleave"]
        stamina_before = self.char1.traits.stamina.current
        with patch("utils.hit_chance.calculate_hit_success", return_value=True):
            result = self.char1.use_skill("cleave", target=self.char2)
        self.assertEqual(self.char1.traits.stamina.current, stamina_before - skill_cls().stamina_cost)
        self.assertTrue(self.char1.cooldowns.time_left("cleave", use_int=True))


    def test_shield_bash_adds_status_effect(self):
        self.char2.hp = 10
        with patch("world.system.stat_manager.check_hit", return_value=True), \
             patch("combat.combat_skills.roll_damage", return_value=4), \
             patch("world.system.state_manager.add_status_effect") as mock_add, \
             patch("utils.hit_chance.calculate_hit_success", return_value=True):
            self.char1.use_skill("shield bash", target=self.char2)
            mock_add.assert_called_with(self.char2, "stunned", 1)
            self.assertEqual(self.char2.hp, 6)

    def test_skill_evade_prevents_damage(self):
        self.char2.hp = 10
        with patch("world.system.stat_manager.check_hit", return_value=True), \
             patch("combat.combat_skills.roll_evade", return_value=True), \
             patch("combat.combat_skills.roll_damage", return_value=4), \
             patch("utils.hit_chance.calculate_hit_success", return_value=True):
            result = self.char1.use_skill("cleave", target=self.char2)
        self.assertEqual(self.char2.hp, 10)
        self.assertIn("misses", result.message)

    def test_skill_hit_check_failure(self):
        skill_cls = SKILL_CLASSES["cleave"]
        stamina_before = self.char1.traits.stamina.current
        with patch("utils.hit_chance.calculate_hit_success", return_value=False):
            result = self.char1.use_skill("cleave", target=self.char2)
        self.assertEqual(self.char1.traits.stamina.current, stamina_before - skill_cls().stamina_cost)
        self.assertTrue(self.char1.cooldowns.time_left("cleave", use_int=True))
        self.assertEqual(result.message, "You miss your strike.")

    def test_spell_cast_failure(self):
        mana_before = self.char1.traits.mana.current
        with patch("utils.hit_chance.calculate_hit_success", return_value=False):
            result = self.char1.cast_spell("fireball", target=self.char2)
        self.assertFalse(result)
        self.assertEqual(self.char1.traits.mana.current, mana_before - SPELLS["fireball"].mana_cost)
        self.assertTrue(self.char1.cooldowns.time_left("fireball", use_int=True))
        self.char1.msg.assert_called_with("You fail to cast the spell.")


    def test_costs_and_cooldowns_on_success_and_failure(self):
        skill_cls = SKILL_CLASSES["cleave"]
        mana_before = self.char1.traits.mana.current
        stamina_before = self.char1.traits.stamina.current
        with patch("utils.hit_chance.calculate_hit_success", side_effect=[True, False]):
            spell_result = self.char1.cast_spell("fireball", target=self.char2)
            skill_result = self.char1.use_skill("cleave", target=self.char2)
        self.assertTrue(spell_result)
        self.assertEqual(skill_result.message, "You miss your strike.")
        self.assertEqual(self.char1.traits.mana.current,
                         mana_before - SPELLS["fireball"].mana_cost)
        self.assertEqual(self.char1.traits.stamina.current,
                         stamina_before - skill_cls().stamina_cost)
        self.assertTrue(self.char1.cooldowns.time_left("fireball", use_int=True))
        self.assertTrue(self.char1.cooldowns.time_left("cleave", use_int=True))

