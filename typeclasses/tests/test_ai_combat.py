import unittest
from unittest.mock import MagicMock

from combat.combat_ai.npc_logic import npc_take_turn
from combat.combat_actions import SpellAction, SkillAction

class DummyNPC:
    def __init__(self):
        self.location = MagicMock()
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
        self.npc = DummyNPC()
        self.target = DummyNPC()
        self.engine = MagicMock()

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
