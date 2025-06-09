"""One time initial setup hooks.

``at_initial_setup`` is only executed once—the very first time the
game's database is created.  Common actions include generating starting
rooms, populating default game objects or creating an administrator
account.  Because it only fires once, mistakes made here require a
database reset to run again, so test carefully.
"""


def at_initial_setup():
    """Hook for custom game setup on first launch."""

    # Example: ensure a starting room exists.
    # from evennia.utils import create
    # if not search_object("Limbo"):  # only run on brand new database
    #     create.create_object("typeclasses.rooms.Room", key="Limbo")
    #
    # Add other game-specific one time setup here.

    pass
