"""Global tick broadcaster."""

from django.dispatch import Signal
from evennia.scripts.scripts import DefaultScript

# ----------------------------------------------------------------------------
# Tick signal
# ----------------------------------------------------------------------------
#
# Other modules can subscribe to this signal to run code once per minute.
# Import ``TICK`` from this module and ``connect`` a handler. Handlers will
# receive ``sender`` as this script instance and any keyword arguments passed
# to :func:`Signal.send`.

TICK = Signal()

class GlobalTick(DefaultScript):
    """Script emitting the :data:`TICK` signal every minute."""

    def at_script_creation(self):
        self.interval = 60
        self.persistent = True

    def at_repeat(self):
        """Broadcast the global tick."""
        TICK.send(sender=self)
