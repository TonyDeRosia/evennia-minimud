"""Global tick broadcaster."""

from django.dispatch import Signal
from evennia.scripts.scripts import DefaultScript
from evennia.utils.search import search_tag

# ----------------------------------------------------------------------------
# Tick signal
# ----------------------------------------------------------------------------
#
# Other modules can subscribe to this signal to run code once per minute.
# Other systems should subscribe to this tick via their own repeating scripts.
# Import ``TICK`` from this module and ``connect`` a handler. Handlers will
# receive ``sender`` as this script instance and any keyword arguments passed
# to :func:`Signal.send`.

TICK = Signal()

class GlobalTickScript(DefaultScript):
    """Script emitting the :data:`TICK` signal every minute."""

    def at_script_creation(self):
        self.interval = 60
        self.persistent = True

    def at_start(self):
        pass

    def at_repeat(self):
        """Handle one global tick."""
        from world.system import state_manager

        for obj in search_tag("tickable"):
            if hasattr(obj, "at_tick"):
                changed = obj.at_tick()
            else:
                changed = bool(state_manager.apply_regen(obj))
            if changed and hasattr(obj, "sessions") and obj.sessions.count():
                if hasattr(obj, "msg"):
                    obj.msg("You have recovered some.")
                if hasattr(obj, "refresh_prompt"):
                    obj.refresh_prompt()

        TICK.send(sender=self)

    def at_stop(self):
        pass
