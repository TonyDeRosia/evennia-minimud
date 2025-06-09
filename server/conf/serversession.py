"""
ServerSession

The serversession is the Server-side in-memory representation of a
user connecting to the game.  Evennia manages one Session per
connection to the game. So a user logged into the game with multiple
clients (if Evennia is configured to allow that) will have multiple
sessions tied to one Account object. All communication between Evennia
and the real-world user goes through the Session(s) associated with that user.

It should be noted that modifying the Session object is not usually
necessary except for the most custom and exotic designs - and even
then it might be enough to just add custom session-level commands to
the SessionCmdSet instead.

This module is not normally called. To tell Evennia to use the class
in this module instead of the default one, add the following to your
settings file:

    SERVER_SESSION_CLASS = "server.conf.serversession.ServerSession"

"""

from evennia.server.serversession import ServerSession as BaseServerSession


class ServerSession(BaseServerSession):
    """Representation of a player's connection to the server."""

    # Evennia already provides a fully featured ``ServerSession``. This
    # subclass exists purely as a customization point for games that want
    # to extend the behaviour of individual sessions.  Typical use cases
    # are storing extra per-session state, overriding connection hooks or
    # adding convenience methods used by your own protocol extensions.

    #  Example: uncomment ``at_disconnect`` to log when a session closes.
    #
    # def at_disconnect(self, reason=None):
    #     """Custom logic whenever this session disconnects."""
    #     self.log(f"Session closed: {reason}")
    #     super().at_disconnect(reason=reason)

    pass
