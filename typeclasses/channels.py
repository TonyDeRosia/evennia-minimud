"""
Channel

The channel class represents the out-of-character chat-room usable by
Accounts in-game. It is mostly overloaded to change its appearance, but
channels can be used to implement many different forms of message
distribution systems.

Note that sending data to channels are handled via the CMD_CHANNEL
syscommand (see evennia.syscmds). The sending should normally not need
to be modified.

"""

from evennia.comms.comms import DefaultChannel
from evennia.utils.utils import make_iter


MAX_HISTORY = 50


class Channel(DefaultChannel):
    """
    Working methods:
        at_channel_creation() - called once, when the channel is created
        has_connection(account) - check if the given account listens to this channel
        connect(account) - connect account to this channel
        disconnect(account) - disconnect account from channel
        access(access_obj, access_type='listen', default=False) - check the
                    access on this channel (default access_type is listen)
        delete() - delete this channel
        message_transform(msg, emit=False, prefix=True,
                          sender_strings=None, external=False) - called by
                          the comm system and triggers the hooks below
        msg(msgobj, header=None, senders=None, sender_strings=None,
            persistent=None, online=False, emit=False, external=False) - main
                send method, builds and sends a new message to channel.
        tempmsg(msg, header=None, senders=None) - wrapper for sending non-persistent
                messages.
        distribute_message(msg, online=False) - send a message to all
                connected accounts on channel, optionally sending only
                to accounts that are currently online (optimized for very large sends)

    Useful hooks:
        channel_prefix() - how the channel should be
                  prefixed when returning to user. Returns a string
        format_senders(senders) - should return how to display multiple
                senders to a channel
        pose_transform(msg, sender_string) - should detect if the
                sender is posing, and if so, modify the string
        format_external(msg, senders, emit=False) - format messages sent
                from outside the game, like from IRC
        format_message(msg, emit=False) - format the message body before
                displaying it to the user. 'emit' generally means that the
                message should not be displayed with the sender's name.

        pre_join_channel(joiner) - if returning False, abort join
        post_join_channel(joiner) - called right after successful join
        pre_leave_channel(leaver) - if returning False, abort leave
        post_leave_channel(leaver) - called right after successful leave
        pre_send_message(msg) - runs just before a message is sent to channel
        post_send_message(msg) - called just after message was sent to channel

    """

    def pre_join_channel(self, joiner, **kwargs):
        """Block joining if joiner has a ``nojoin`` tag."""

        if joiner.tags.get("nojoin", category="channel"):
            joiner.msg(f"You may not join {self.key}.")
            return False
        return True

    def post_join_channel(self, joiner, **kwargs):
        """Announce the join and run parent hook."""

        super().post_join_channel(joiner, **kwargs)
        self.msg(f"{joiner.key} has joined {self.key}.")

    def pre_leave_channel(self, leaver, **kwargs):
        """Prevent leaving if the ``noleave`` tag is set."""

        if leaver.tags.get("noleave", category="channel"):
            leaver.msg(f"You may not leave {self.key}.")
            return False
        return True

    def post_leave_channel(self, leaver, **kwargs):
        """Announce the leave and run parent hook."""

        super().post_leave_channel(leaver, **kwargs)
        self.msg(f"{leaver.key} has left {self.key}.")

    def pre_send_message(self, msg, **kwargs):
        """Block messages from senders tagged ``muted``."""

        for sender in make_iter(kwargs.get("senders", [])):
            if sender.tags.get("muted", category="channel"):
                sender.msg("You are muted and cannot speak here.")
                return False
        return msg

    def post_send_message(self, msg, **kwargs):
        """Store a simple history of recent messages."""

        history = list(self.db.history or [])
        history.append(msg)
        self.db.history = history[-MAX_HISTORY:]

    # new-style hooks calling the old-style names
    def at_pre_msg(self, message, **kwargs):
        message = self.pre_send_message(message, **kwargs)
        if message in (None, False):
            return None
        return super().at_pre_msg(message, **kwargs)

    def at_post_msg(self, message, **kwargs):
        super().at_post_msg(message, **kwargs)
        self.post_send_message(message, **kwargs)
