"""Global tick broadcaster."""

from django.dispatch import Signal
from evennia.scripts.scripts import DefaultScript
from typeclasses.characters import Character, NPC

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

    def at_repeat(self):
        """Handle one global tick."""
        targets = list(Character.objects.all()) + list(NPC.objects.all())
        seen = set()
        for obj in targets:
            if obj in seen:
                continue
            seen.add(obj)
            if hasattr(obj, "at_tick"):
                changed = obj.at_tick()
                if changed and obj.sessions.count():
                    obj.msg("You have recovered some.")
                    obj.refresh_prompt()

        TICK.send(sender=self)
