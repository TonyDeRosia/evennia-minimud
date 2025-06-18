"""Utilities for handling room directions and exit ordering."""

# Preferred display order for cardinal exits.
EXIT_DISPLAY_ORDER = ["north", "south", "west", "east"]


def sort_exit_names(names):
    """Return ``names`` sorted using ``EXIT_DISPLAY_ORDER``."""
    order_map = {name: idx for idx, name in enumerate(EXIT_DISPLAY_ORDER)}
    return sorted(names, key=lambda n: (order_map.get(n.lower(), len(EXIT_DISPLAY_ORDER)), n))
