import unittest
from unittest.mock import MagicMock

from combat.ai_combat import npc_take_turn
from combat.combat_actions import SpellAction, SkillAction
from combat.combat_skills import SKILL_CLASSES

DEFAULT_LOCATION = MagicMock()

class DummyNPC:
    def __init__(self, location=None):
        self.location = location or DEFAULT_LOCATION
        self.hp = 20
        self.traits = MagicMock()
        self.traits.health = MagicMock(value=20, max=20)
        self.traits.mana = MagicMock(current=20)
        self.traits.stamina = MagicMock(current=20)
        self.cooldowns = MagicMock()
        self.cooldowns.ready.return_value = True
        self.db = MagicMock()
        self.db.spells = ["fireball"]
        self.db.skills = ["cleave"]
        self.wielding = []
        self.attack = MagicMock()
        self.cast_spell = MagicMock()
        self.use_skill = MagicMock()

class TestAICombat(unittest.TestCase):
    def setUp(self):
        loc = MagicMock()
        self.npc = DummyNPC(loc)
        self.target = DummyNPC(loc)
        self.engine = MagicMock()
        # Provide simple skill stubs that don't require init args
        class _Cleave:
            name = "cleave"
            stamina_cost = 20
            cooldown = 8

            def resolve(self, user, target):
                pass

        class _ShieldBash(_Cleave):
            name = "shield bash"
            stamina_cost = 15

        SKILL_CLASSES["cleave"] = _Cleave
        SKILL_CLASSES["shield bash"] = _ShieldBash

    def test_prefers_spell_over_skill(self):
        npc_take_turn(self.engine, self.npc, self.target)
        action = self.engine.queue_action.call_args[0][1]
        self.assertIsInstance(action, SpellAction)

    def test_uses_skill_when_no_mana(self):
        self.npc.traits.mana.current = 0
        self.engine.queue_action.reset_mock()
        npc_take_turn(self.engine, self.npc, self.target)
        action = self.engine.queue_action.call_args[0][1]
        self.assertIsInstance(action, SkillAction)

    def test_spell_order(self):
        self.npc.db.spells = ["fireball", "heal"]
        npc_take_turn(self.engine, self.npc, self.target)
        action = self.engine.queue_action.call_args[0][1]
        self.assertIsInstance(action, SpellAction)
        self.assertEqual(action.spell.key, "fireball")

    def test_spell_fallback_to_next(self):
        self.npc.db.spells = ["fireball", "heal"]
        self.npc.traits.mana.current = 8
        self.engine.queue_action.reset_mock()
        npc_take_turn(self.engine, self.npc, self.target)
        action = self.engine.queue_action.call_args[0][1]
        self.assertIsInstance(action, SpellAction)
        self.assertEqual(action.spell.key, "heal")

    def test_skill_order(self):
        self.npc.db.spells = []
        self.npc.db.skills = ["cleave", "shield bash"]
        npc_take_turn(self.engine, self.npc, self.target)
        action = self.engine.queue_action.call_args[0][1]
        self.assertIsInstance(action, SkillAction)
        self.assertEqual(action.skill.name, "cleave")

    def test_skill_fallback_to_next(self):
        self.npc.db.spells = []
        self.npc.db.skills = ["cleave", "shield bash"]
        self.npc.traits.stamina.current = 15
        self.engine.queue_action.reset_mock()
        npc_take_turn(self.engine, self.npc, self.target)
        action = self.engine.queue_action.call_args[0][1]
        self.assertIsInstance(action, SkillAction)
        self.assertEqual(action.skill.name, "shield bash")

    def test_attack_action_uses_combat_math(self):
        """Ensure NPC basic attacks rely on CombatMath helpers."""

        self.npc.db.spells = []
        self.npc.db.skills = []
        self.engine.queue_action.reset_mock()
        npc_take_turn(self.engine, self.npc, self.target)
        action = self.engine.queue_action.call_args[0][1]
        with patch("combat.combat_actions.CombatMath.check_hit", return_value=(True, "")) as mock_hit, \
             patch("combat.combat_actions.CombatMath.calculate_damage", return_value=(5, None)), \
             patch("combat.combat_actions.CombatMath.apply_critical", return_value=(5, False)):
            action.resolve()
        mock_hit.assert_called()
