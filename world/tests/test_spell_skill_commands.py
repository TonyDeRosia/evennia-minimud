from unittest.mock import patch, MagicMock
from evennia.utils.test_resources import EvenniaTest
from world.spells import SPELLS


class TestSpellAndSkillCommands(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.char1.db.spells = [SPELLS["fireball"]]
        self.char1.db.skills = ["kick"]
        self.char1.location.msg_contents = MagicMock()

    def test_cmd_cast_applies_cost_and_cooldown(self):
        mana_before = self.char1.traits.mana.current
        self.char1.execute_cmd(f"cast fireball {self.char2.key}")
        self.assertEqual(
            self.char1.traits.mana.current,
            mana_before - SPELLS["fireball"].mana_cost,
        )
        self.assertTrue(self.char1.cooldowns.time_left("fireball", use_int=True))

    def test_auto_skill_command_calls_use_skill(self):
        with patch.object(self.char1, "use_skill", return_value=MagicMock(message="hit")) as mock_use:
            self.char1.execute_cmd(f"kick {self.char2.key}")
            mock_use.assert_called_with("kick", target=self.char2)
            self.char1.location.msg_contents.assert_called_with("hit")

    def test_auto_skill_command_generated_for_skill_classes(self):
        self.char1.db.skills.append("cleave")
        self.char1.location.msg_contents.reset_mock()
        with patch.object(self.char1, "use_skill", return_value=MagicMock(message="hit")) as mock_use:
            self.char1.execute_cmd(f"cleave {self.char2.key}")
            mock_use.assert_called_with("cleave", target=self.char2)
            self.char1.location.msg_contents.assert_called_with("hit")
