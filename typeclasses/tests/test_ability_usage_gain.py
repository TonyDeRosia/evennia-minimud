from evennia.utils.test_resources import EvenniaTest
from world.system import state_manager, proficiency_manager
from world.system.proficiency_manager import USE_CAP


class TestAbilityUsageGain(EvenniaTest):
    def setUp(self):
        super().setUp()
        state_manager.grant_ability(self.char1, "kick", proficiency=33, mark_new=False)
        state_manager.grant_ability(
            self.char1, "fireball", proficiency=99, mark_new=False
        )
        self.kick_trait = self.char1.traits.get("kick")
        for entry in self.char1.db.spells:
            if entry.key == "fireball":
                self.fireball = entry
                break

    def test_skill_usage_increases_proficiency(self):
        for _ in range(25):
            proficiency_manager.record_use(self.char1, self.kick_trait)
        self.assertEqual(self.kick_trait.proficiency, 34)

    def test_spell_usage_caps_at_100(self):
        for _ in range(25):
            proficiency_manager.record_use(self.char1, self.fireball)
        self.assertEqual(self.fireball.proficiency, USE_CAP)
        for _ in range(25):
            proficiency_manager.record_use(self.char1, self.fireball)
        self.assertEqual(self.fireball.proficiency, USE_CAP)
