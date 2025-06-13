"""One time initial setup hooks.

``at_initial_setup`` is only executed once—the very first time the
game's database is created.  Common actions include generating starting
rooms, populating default game objects or creating an administrator
account.  Because it only fires once, mistakes made here require a
database reset to run again, so test carefully.
"""


from evennia import create_object
from evennia.utils import logger, search
from evennia.accounts.models import AccountDB
from world.areas import Area, save_area


def _create_start_room():
    """Create the initial starting room if it doesn't exist."""

    room = search.search_object("Town Square")
    if room:
        return room[0]

    room = create_object(
        "typeclasses.rooms.Room",
        key="Town Square",
    )
    room.db.desc = "The bustling center of town where new adventurers gather."
    logger.log_info("Created starting room: Town Square")
    return room


def _create_admin_account(start_room):
    """Ensure a default admin account exists."""

    if AccountDB.objects.filter(username__iexact="admin").exists():
        return

    admin = AccountDB.objects.create_superuser(
        "admin",
        "admin@example.com",
        "adminpass",
    )
    char, errors = admin.create_character(key="Admin", nohome=True)
    if not errors:
        char.home = start_room
        char.location = start_room
        char.save()
    logger.log_info("Created default admin account 'admin'")


def _create_default_area():
    """Create a basic starting area entry."""

    area = Area(key="Starter Zone", start=200000, end=200999)
    save_area(area)
    logger.log_info("Registered starting area 'Starter Zone'")


def at_initial_setup():
    """Hook for custom game setup on first launch."""

    start_room = _create_start_room()
    _create_admin_account(start_room)
    _create_default_area()

