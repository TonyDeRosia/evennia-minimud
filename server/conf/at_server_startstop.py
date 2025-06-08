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
    """
    This is called first as the server is starting up, regardless of how.
    """
    pass


def at_server_start():
    """
    This is called every time the server starts up, regardless of
    how it was shut down.
    """
    from evennia.utils import create
    from evennia.scripts.models import ScriptDB

    scripts = list(ScriptDB.objects.filter(db_key="global_tick"))
    script = None
    if scripts:
        script = scripts[0]
        for extra in scripts[1:]:
            extra.stop()
            extra.delete()

    if script and script.typeclass_path != "typeclasses.global_tick.GlobalTickScript":
        script.stop()
        script.delete()
        script = None

    if script:
        # Make sure the script is configured correctly
        changed = False
        if script.interval != 60:
            script.interval = 60
            changed = True
        if not script.persistent:
            script.persistent = True
            changed = True
        if changed:
            script.save()
            script.restart()
        elif not script.is_active:
            script.start()

    if not script:
        script = create.create_script("typeclasses.global_tick.GlobalTickScript", key="global_tick")
        script.start()

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
    pass


def at_server_reload_start():
    """
    This is called only when server starts back up after a reload.
    """
    pass


def at_server_reload_stop():
    """
    This is called only time the server stops before a reload.
    """
    pass


def at_server_cold_start():
    """
    This is called only when the server starts "cold", i.e. after a
    shutdown or a reset.
    """
    pass


def at_server_cold_stop():
    """
    This is called only when the server goes down due to a shutdown or
    reset.
    """
    pass
