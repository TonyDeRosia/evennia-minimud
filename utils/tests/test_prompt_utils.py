from unittest.mock import MagicMock

from evennia.utils.test_resources import EvenniaTest


class TestDisplayAutoPrompt(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.char1.account = MagicMock()
        self.char1.account.db.settings = {"auto prompt": True}
        self.char1.get_display_status = MagicMock(return_value="STATUS")

    def test_prompt_sent_when_enabled(self):
        from utils import display_auto_prompt

        send = MagicMock()
        display_auto_prompt(self.char1.account, self.char1, send)
        send.assert_called_with(prompt="STATUS")

    def test_no_prompt_when_disabled(self):
        from utils import display_auto_prompt

        self.char1.account.db.settings["auto prompt"] = False
        send = MagicMock()
        display_auto_prompt(self.char1.account, self.char1, send)
        send.assert_not_called()

    def test_force_override(self):
        from utils import display_auto_prompt

        self.char1.account.db.settings["auto prompt"] = False
        send = MagicMock()
        display_auto_prompt(self.char1.account, self.char1, send, force=True)
        send.assert_called_with(prompt="STATUS")
