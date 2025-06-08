"""Global tick broadcaster."""

from django.dispatch import Signal
from evennia.scripts.scripts import DefaultScript
from typeclasses.characters import Character

# registry of character IDs that should receive ticks
REGISTERED = set()
# mapping of registered IDs to character objects for fast access
REGISTERED_OBJS = {}
_SCRIPT = None


def register_character(char):
    """Add a character to the tick registry."""
    REGISTERED.add(char.id)
    REGISTERED_OBJS[char.id] = char
    if _SCRIPT:
        _SCRIPT.db.registry = list(REGISTERED)


def unregister_character(char):
    """Remove a character from the tick registry."""
    REGISTERED.discard(char.id)
    REGISTERED_OBJS.pop(char.id, None)
    if _SCRIPT:
        _SCRIPT.db.registry = list(REGISTERED)

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
        if self.db.registry is None:
            self.db.registry = []

    def at_start(self):
        global _SCRIPT, REGISTERED, REGISTERED_OBJS
        _SCRIPT = self
        REGISTERED.update(self.db.registry or [])
        # cache object references for all stored ids
        for cid in list(REGISTERED):
            try:
                REGISTERED_OBJS[cid] = Character.objects.get(id=cid)
            except Character.DoesNotExist:
                pass

    def at_repeat(self):
        """Handle one global tick."""
        global REGISTERED, REGISTERED_OBJS
        dead_ids = []
        for cid in list(REGISTERED):
            obj = REGISTERED_OBJS.get(cid)
            if obj is None:
                try:
                    obj = Character.objects.get(id=cid)
                    REGISTERED_OBJS[cid] = obj
                except Character.DoesNotExist:
                    dead_ids.append(cid)
                    continue
            if obj.pk is None:
                dead_ids.append(cid)
                REGISTERED_OBJS.pop(cid, None)
                continue
            if hasattr(obj, "at_tick"):
                changed = obj.at_tick()
                if changed and obj.sessions.count():
                    obj.msg("You have recovered some.")
                    obj.refresh_prompt()
        for cid in dead_ids:
            REGISTERED.discard(cid)
        self.db.registry = list(REGISTERED)

        TICK.send(sender=self)

    def at_stop(self):
        global _SCRIPT
        self.db.registry = list(REGISTERED)
        _SCRIPT = None
