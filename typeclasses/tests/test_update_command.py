from unittest.mock import MagicMock, patch
from django.test import override_settings
from evennia.utils.test_resources import EvenniaTest
from commands.admin import AdminCmdSet
from world.system.class_skills import get_class_skills
from world.system import state_manager


@override_settings(DEFAULT_HOME=None)
class TestUpdateCommand(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.char1.msg = MagicMock()
        self.char1.cmdset.add_default(AdminCmdSet)
        self.char2.db.charclass = "Warrior"
        self.char2.db.level = 3
        self.char2.db.skills = ["kick"]
        self.expected = get_class_skills("Warrior", 3)

    def test_update_grants_missing_skills(self):
        with patch("commands.update.state_manager.grant_ability", wraps=state_manager.grant_ability) as mock_grant:
            self.char1.execute_cmd(f"update {self.char2.key}")

        called = [call.args[1] for call in mock_grant.call_args_list]
        assert called == self.expected
        for skill in self.expected:
            assert skill in self.char2.db.skills
