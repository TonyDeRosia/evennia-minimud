"""Event NPC role mixin."""

class EventNPCRole:
    """Mixin for starting or interacting with special events."""

    def start_event(self, caller, event_key: str) -> None:
        """Initiate an event identified by `event_key`."""
        if not caller or not event_key:
            return
        caller.msg(f"{self.key} begins the event '{event_key}'.")
