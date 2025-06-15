from unittest.mock import MagicMock, patch
from django.test import override_settings
from evennia.utils.test_resources import EvenniaTest
from commands.abilities import AbilityCmdSet
from world.skills.kick import Kick
from combat.combat_actions import SkillAction
from world.system import state_manager


@override_settings(DEFAULT_HOME=None)
class TestKickSkill(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.char1.msg = MagicMock()
        self.char1.cmdset.add_default(AbilityCmdSet)
        self.char1.db.skills = ["kick"]
        self.char1.db.proficiencies = {"kick": 0}

    def test_cmd_skills_lists_known(self):
        self.char1.execute_cmd("skills")
        out = self.char1.msg.call_args[0][0]
        self.assertIn("Skill", out)
        self.assertIn("Proficiency", out)
        self.assertIn("kick", out)
        self.assertIn("0%", out)

    def test_kick_applies_cost_and_improves(self):
        skill = Kick()
        stamina_before = self.char1.traits.stamina.current
        # dummy combat engine that resolves action immediately
        class DummyEngine:
            def queue_action(self, actor, action):
                action.resolve()

        class DummyCombat:
            def __init__(self):
                self.engine = DummyEngine()

        with patch("commands.abilities.maybe_start_combat", return_value=DummyCombat()), \
             patch("world.skills.skill.random", return_value=0):
            self.char1.execute_cmd(f"kick {self.char2.key}")

        self.assertEqual(
            self.char1.traits.stamina.current,
            stamina_before - skill.stamina_cost,
        )
        self.assertTrue(self.char1.cooldowns.time_left(skill.name, use_int=True))
        self.assertEqual(self.char1.db.proficiencies["kick"], 1)

