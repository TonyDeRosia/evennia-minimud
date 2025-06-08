"""Event NPC role mixin."""

class EventNPCRole:
    """Mixin for starting or interacting with special events."""

    def start_event(self, caller, event_key: str) -> None:
        """Trigger an in-game event using ``event_key``."""
        if not caller or not event_key:
            return

        self.db.active_event = event_key
        caller.msg(f"{self.key} begins the event '{event_key}'.")
