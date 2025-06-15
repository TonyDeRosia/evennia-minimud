from unittest.mock import patch, MagicMock
from django.test import override_settings
from evennia.utils.test_resources import EvenniaTest
from combat.combat_skills import SKILL_CLASSES
from world.spells import SPELLS

@override_settings(DEFAULT_HOME=None)
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


    def test_shield_bash_adds_status_effect(self):
        self.char2.hp = 10
        with patch("world.system.stat_manager.check_hit", return_value=True), \
             patch("combat.combat_skills.roll_damage", return_value=4), \
              patch("world.system.state_manager.add_status_effect") as mock_add:
            self.char1.use_skill("shield bash", target=self.char2)
            mock_add.assert_called_with(self.char2, "stunned", 1)
            self.assertEqual(self.char2.hp, 6)

    def test_skill_evade_prevents_damage(self):
        self.char2.hp = 10
        with patch("world.system.stat_manager.check_hit", return_value=True), \
             patch("combat.combat_skills.roll_evade", return_value=True), \
              patch("combat.combat_skills.roll_damage", return_value=4):
            result = self.char1.use_skill("cleave", target=self.char2)
        self.assertEqual(self.char2.hp, 10)
        self.assertIn("misses", result.message)

    def test_use_skill_records_proficiency(self):
        from world.system import state_manager
        from combat.combat_actions import CombatResult
        from combat.combat_skills import Cleave

        state_manager.grant_ability(self.char1, "cleave", mark_new=False)

        with patch("world.system.proficiency_manager.record_use") as mock_rec, \
             patch.object(Cleave, "resolve", return_value=CombatResult(actor=self.char1, target=self.char2, message="hit")):
            self.char1.use_skill("cleave", target=self.char2)
            skill_trait = self.char1.traits.get("cleave")
            mock_rec.assert_called_with(self.char1, skill_trait)

    def test_skill_use_starts_combat(self):
        with patch("combat.combat_skills.maybe_start_combat") as mock_start, \
             patch("world.system.stat_manager.check_hit", return_value=True), \
             patch("combat.combat_skills.roll_evade", return_value=False), \
             patch("combat.combat_skills.roll_damage", return_value=3):
            self.char1.use_skill("cleave", target=self.char2)
            mock_start.assert_called_with(self.char1, self.char2)

    def test_spell_cast_starts_combat(self):
        with patch("combat.combat_utils.maybe_start_combat") as mock_start, \
             patch("world.system.state_manager.add_cooldown"), \
             patch.object(self.char1, "location"):
            self.char1.cast_spell("fireball", target=self.char2)
            mock_start.assert_called_with(self.char1, self.char2)

    def test_maybe_start_combat_sets_targets(self):
        """Starting combat should set combat_target on both combatants."""
        from combat.combat_utils import maybe_start_combat

        with patch("combat.round_manager.CombatRoundManager.get") as mock_get:
            manager = MagicMock()
            mock_get.return_value = manager
            manager.get_combatant_combat.return_value = None

            maybe_start_combat(self.char1, self.char2)

            manager.start_combat.assert_called_with([self.char1, self.char2])
            self.assertEqual(self.char1.db.combat_target, self.char2)
            self.assertEqual(self.char2.db.combat_target, self.char1)

    def test_maybe_start_combat_preserves_existing_targets(self):
        """Existing combat_target settings pointing elsewhere are kept."""
        from combat.combat_utils import maybe_start_combat

        other1 = MagicMock()
        other2 = MagicMock()
        self.char1.db.combat_target = other1
        self.char2.db.combat_target = other2

        with patch("combat.round_manager.CombatRoundManager.get") as mock_get:
            manager = MagicMock()
            mock_get.return_value = manager
            manager.get_combatant_combat.return_value = None

            maybe_start_combat(self.char1, self.char2)

            manager.start_combat.assert_called_with([self.char1, self.char2])
            self.assertIs(self.char1.db.combat_target, other1)
            self.assertIs(self.char2.db.combat_target, other2)

    def test_maybe_start_combat_updates_missing_target(self):
        """If only one fighter targets the other, both should after starting."""
        from combat.combat_utils import maybe_start_combat

        self.char1.db.combat_target = self.char2
        self.char2.db.combat_target = None

        with patch("combat.round_manager.CombatRoundManager.get") as mock_get:
            manager = MagicMock()
            mock_get.return_value = manager
            manager.get_combatant_combat.return_value = None

            maybe_start_combat(self.char1, self.char2)

            manager.start_combat.assert_called_with([self.char1, self.char2])
            self.assertIs(self.char1.db.combat_target, self.char2)
            self.assertIs(self.char2.db.combat_target, self.char1)

    def test_use_skill_sets_combat_targets(self):
        """Using a skill should set combat_target on both combatants."""
        with patch("combat.round_manager.CombatRoundManager.get") as mock_get, \
             patch("world.system.stat_manager.check_hit", return_value=True), \
             patch("combat.combat_skills.roll_evade", return_value=False), \
             patch("combat.combat_skills.roll_damage", return_value=1):
            manager = MagicMock()
            mock_get.return_value = manager
            manager.get_combatant_combat.return_value = None

            self.char1.use_skill("cleave", target=self.char2)

            manager.start_combat.assert_called_with([self.char1, self.char2])
            self.assertEqual(self.char1.db.combat_target, self.char2)
            self.assertEqual(self.char2.db.combat_target, self.char1)

    def test_maybe_start_combat_unset_other_target(self):
        """If only one fighter has a combat_target set, both should after starting."""
        from combat.combat_utils import maybe_start_combat

        self.char1.db.combat_target = self.char2
        # ensure the second combatant has no combat_target attribute
        self.char2.attributes.remove("combat_target", raise_exception=False)

        with patch("combat.round_manager.CombatRoundManager.get") as mock_get:
            manager = MagicMock()
            mock_get.return_value = manager
            manager.get_combatant_combat.return_value = None

            maybe_start_combat(self.char1, self.char2)

            manager.start_combat.assert_called_with([self.char1, self.char2])
            self.assertIs(self.char1.db.combat_target, self.char2)
            self.assertIs(self.char2.db.combat_target, self.char1)

