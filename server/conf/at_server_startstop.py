"""
Server startstop hooks

This module contains functions called by Evennia at various
points during its startup, reload and shutdown sequence. It
allows for customizing the server operation as desired.

This module must contain at least these global functions:

at_server_init()
at_server_start()
at_server_stop()
at_server_reload_start()
at_server_reload_stop()
at_server_cold_start()
at_server_cold_stop()

"""


def at_server_init():
    """Called as the service layer initializes."""

    from evennia.utils.logger import log_info

    # Example custom behavior: populate in-memory caches or pre-load data.
    log_info("at_server_init: building caches")

    # add initialization code here

    pass


def at_server_start():
    """
    This is called every time the server starts up, regardless of
    how it was shut down.
    """
    from evennia.utils import create
    from evennia.scripts.models import ScriptDB
    from world.scripts.mob_db import get_mobdb

    script = ScriptDB.objects.filter(db_key="global_tick").first()
    if not script or script.typeclass_path != "typeclasses.scripts.GlobalTick":
        if script:
            script.delete()
        create.create_script("typeclasses.scripts.GlobalTick", key="global_tick")

    # Ensure mob database script exists
    get_mobdb()

    # Ensure all characters are marked tickable for the global ticker
    from typeclasses.characters import Character

    for char in Character.objects.all():
        if not char.tags.has("tickable"):
            char.tags.add("tickable")


def at_server_stop():
    """
    This is called just before the server is shut down, regardless
    of it is for a reload, reset or shutdown.
    """
    from evennia.utils.logger import log_info

    log_info("at_server_stop: cleaning up")

    # add shutdown logic here

    pass


def at_server_reload_start():
    """
    This is called only when server starts back up after a reload.
    """
    from evennia.utils.logger import log_info

    log_info("at_server_reload_start: preparing reload")

    # add reload-start logic here

    pass


def at_server_reload_stop():
    """
    This is called only time the server stops before a reload.
    """
    from evennia.utils.logger import log_info

    log_info("at_server_reload_stop: reload complete")

    # add reload-stop logic here

    pass


def at_server_cold_start():
    """
    This is called only when the server starts "cold", i.e. after a
    shutdown or a reset.
    """
    from evennia.utils.logger import log_info

    log_info("at_server_cold_start: cold boot")

    # add cold-start logic here

    pass


def at_server_cold_stop():
    """
    This is called only when the server goes down due to a shutdown or
    reset.
    """
    from evennia.utils.logger import log_info

    log_info("at_server_cold_stop: shutting down")

    # add cold-stop logic here

    pass
