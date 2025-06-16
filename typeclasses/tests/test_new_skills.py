from unittest.mock import MagicMock, patch
from django.test import override_settings
from evennia.utils.test_resources import EvenniaTest
from commands.abilities import AbilityCmdSet
from world.skills.kick import Kick
from world.system import stat_manager
from combat.damage_types import DamageType


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

    def test_kick_auto_targets_current_opponent(self):
        self.char1.db.in_combat = True
        self.char1.db.combat_target = self.char2
        self.char2.at_damage = MagicMock()

        class DummyEngine:
            def queue_action(self, actor, action):
                action.resolve()

        class DummyCombat:
            def __init__(self):
                self.engine = DummyEngine()

        with patch("commands.abilities.maybe_start_combat", return_value=DummyCombat()), \
             patch.object(stat_manager, "check_hit", return_value=True), \
             patch("combat.combat_utils.roll_evade", return_value=False), \
             patch.object(stat_manager, "get_effective_stat", return_value=10), \
             patch("world.skills.skill.random", return_value=0):
            self.char1.execute_cmd("kick")

        self.char2.at_damage.assert_called()

    def test_kick_damage_scales_with_strength(self):
        self.char2.at_damage = MagicMock()
        self.room1.msg_contents = MagicMock()

        class DummyEngine:
            def queue_action(self, actor, action):
                action.resolve()

        class DummyCombat:
            def __init__(self):
                self.engine = DummyEngine()

        with patch("commands.abilities.maybe_start_combat", return_value=DummyCombat()), \
             patch.object(stat_manager, "check_hit", return_value=True), \
             patch("combat.combat_utils.roll_evade", return_value=False), \
             patch.object(stat_manager, "get_effective_stat", return_value=20), \
             patch("world.skills.skill.random", return_value=0):
            self.char1.execute_cmd(f"kick {self.char2.key}")

        expected = int(5 + 20 * 0.2)
        self.char2.at_damage.assert_called_with(self.char1, expected, DamageType.BLUDGEONING)
        msg = f"{self.char1.key} kicks {self.char2.key} for {expected} damage!"
        self.room1.msg_contents.assert_called_with(msg)

    def test_kick_numbered_target(self):
        """Ensure numbered aliases target the correct enemy."""
        from evennia.utils import create
        from typeclasses.npcs import BaseNPC

        slime1 = create.create_object(BaseNPC, key="slime", location=self.room1)
        slime2 = create.create_object(BaseNPC, key="slime", location=self.room1)

        class DummyEngine:
            def queue_action(self, actor, action):
                action.resolve()

        class DummyCombat:
            def __init__(self):
                self.engine = DummyEngine()

        with patch("commands.abilities.maybe_start_combat", return_value=DummyCombat()), \
             patch.object(stat_manager, "check_hit", return_value=True), \
             patch("combat.combat_utils.roll_evade", return_value=False), \
             patch.object(stat_manager, "get_effective_stat", return_value=10), \
             patch("world.skills.skill.random", return_value=0):
            self.char1.execute_cmd("kick slime-2")

        self.assertEqual(self.char1.db.combat_target, slime2)

