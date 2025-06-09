import unittest
from unittest.mock import MagicMock

from combat.ai_combat import npc_take_turn
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
