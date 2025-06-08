from unittest.mock import MagicMock

from evennia.utils import create
from evennia.utils.test_resources import EvenniaTest
from django.test import override_settings

from typeclasses.channels import Channel


@override_settings(DEFAULT_HOME=None)
class TestChannelHooks(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.char1.account.msg = MagicMock()
        self.char2.account.msg = MagicMock()
        self.channel = create.create_channel("TestChan", typeclass=Channel)
        self.channel.connect(self.char2)
        self.char2.account.msg.reset_mock()

    def test_pre_join_block(self):
        self.char1.tags.add("nojoin", category="channel")
        joined = self.channel.connect(self.char1)
        self.assertFalse(joined)
        self.char1.account.msg.assert_called_with("You may not join TestChan.")

    def test_join_and_leave_announcements(self):
        self.channel.connect(self.char1)
        self.assertTrue(self.char1 in self.channel.subscriptions.all())
        self.char1.account.msg.assert_any_call("Char has joined TestChan.")
        self.char2.account.msg.reset_mock()
        self.channel.disconnect(self.char1)
        self.assertFalse(self.channel.subscriptions.has(self.char1))
        self.char1.account.msg.assert_any_call("Char has left TestChan.")

    def test_pre_send_block_and_history(self):
        self.channel.connect(self.char1)
        self.char1.tags.add("muted", category="channel")
        len_before = len(self.channel.db.history or [])
        self.channel.msg("hi", senders=self.char1)
        self.char1.account.msg.assert_called_with("You are muted and cannot speak here.")
        self.assertEqual(len(self.channel.db.history or []), len_before)
        self.char1.tags.remove("muted", category="channel")
        self.channel.msg("hello", senders=self.char1)
        self.assertEqual(self.channel.db.history[-1], "hello")
        self.char1.account.msg.assert_any_call("hello")

