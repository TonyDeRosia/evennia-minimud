from evennia.utils.test_resources import EvenniaTest
from combat.combat_skills import SKILL_CLASSES
from world.spells import SPELLS

class TestSkillAndSpellUsage(EvenniaTest):
    def setUp(self):
        super().setUp()
        # ensure characters have sample spell known
        self.char1.db.spells = [SPELLS["fireball"]]

    def test_cast_spell_applies_cost_and_cooldown(self):
        mana_before = self.char1.traits.mana.current
        result = self.char1.cast_spell("fireball", target=self.char2)
        self.assertTrue(result)
        self.assertEqual(self.char1.traits.mana.current, mana_before - SPELLS["fireball"].mana_cost)
        self.assertTrue(self.char1.cooldowns.time_left("fireball", use_int=True))

    def test_use_skill_applies_cost_and_cooldown(self):
        skill_cls = SKILL_CLASSES["cleave"]
        stamina_before = self.char1.traits.stamina.current
        result = self.char1.use_skill("cleave", target=self.char2)
        self.assertEqual(self.char1.traits.stamina.current, stamina_before - skill_cls().stamina_cost)
        self.assertTrue(self.char1.cooldowns.time_left("cleave", use_int=True))

