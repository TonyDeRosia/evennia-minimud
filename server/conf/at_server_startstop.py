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

# Path to the global tick script typeclass
GLOBAL_TICK_SCRIPT_PATH = "typeclasses.global_tick.GlobalTickScript"
# Path to the global healing script typeclass
GLOBAL_HEALING_SCRIPT_PATH = "typeclasses.global_healing.GlobalHealingScript"


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

    if script and script.typeclass_path != GLOBAL_TICK_SCRIPT_PATH:
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
        script = create.create_script(GLOBAL_TICK_SCRIPT_PATH, key="global_tick")
        script.start()

    # ------------------------------------------------------------------
    # Global healing script
    # ------------------------------------------------------------------
    scripts = list(ScriptDB.objects.filter(db_key="global_healing"))
    script = None
    if scripts:
        script = scripts[0]
        for extra in scripts[1:]:
            extra.stop()
            extra.delete()

    if script and script.typeclass_path != GLOBAL_HEALING_SCRIPT_PATH:
        script.stop()
        script.delete()
        script = None

    if script:
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
        script = create.create_script(GLOBAL_HEALING_SCRIPT_PATH, key="global_healing")
        script.start()



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
