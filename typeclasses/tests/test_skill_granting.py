from unittest.mock import patch
from evennia.utils.test_resources import EvenniaTest
from commands.abilities import AbilityCmdSet
from world.skills.kick import Kick
from world.system import state_manager

class TestGrantAbility(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.char1.cmdset.add_default(AbilityCmdSet)
        self.char1.msg = lambda *args, **kwargs: None
        state_manager.grant_ability(self.char1, "kick")

    def test_grant_persists(self):
        self.assertIn("kick", self.char1.db.skills)
        self.assertEqual(self.char1.db.proficiencies.get("kick"), 0)
        self.assertEqual(self.char1.db.skill_uses.get("kick"), 0)

    def test_use_tracks_progress(self):
        class DummyEngine:
            def queue_action(self, actor, action):
                action.resolve()

        class DummyCombat:
            def __init__(self):
                self.engine = DummyEngine()

        self.char1.db.skill_uses["kick"] = 24
        with patch("commands.abilities.maybe_start_combat", return_value=DummyCombat()), \
             patch("world.skills.skill.random", return_value=1):
            self.char1.execute_cmd(f"kick {self.char2.key}")

        self.assertEqual(self.char1.db.skill_uses["kick"], 25)
        self.assertEqual(self.char1.db.proficiencies["kick"], 1)

