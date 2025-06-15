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


import time

from evennia.utils import logger
from evennia.server.models import ServerConfig
from utils.prototype_manager import load_all_prototypes


_PROTOTYPE_CACHE = {}


def _build_caches():
    """Load prototypes into memory for quick access."""

    _PROTOTYPE_CACHE["room"] = load_all_prototypes("room")
    _PROTOTYPE_CACHE["npc"] = load_all_prototypes("npc")
    _PROTOTYPE_CACHE["object"] = load_all_prototypes("object")
    logger.log_info("Prototype cache built")


def _clear_caches():
    """Clear the in-memory caches."""

    _PROTOTYPE_CACHE.clear()
    logger.log_info("Prototype cache cleared")


def _migrate_experience():
    """Copy old ``exp`` attributes to ``experience`` if needed."""

    from typeclasses.characters import Character
    from typeclasses.npcs import BaseNPC

    migrated = 0
    for char in Character.objects.all():
        if char.attributes.has("exp"):
            if not char.attributes.has("experience"):
                char.db.experience = char.db.exp
            char.attributes.remove("exp")
            migrated += 1

    if migrated:
        logger.log_info(f"Migrated experience on {migrated} characters")


def _backfill_abilities():
    """Ensure all characters know abilities for their current level."""
    try:
        from scripts.backfill_abilities import backfill
    except Exception as err:
        logger.log_err(f"Ability backfill failed to import: {err}")
    else:
        backfill()


def at_server_init():
    """Called as the service layer initializes."""

    logger.log_info("at_server_init: building caches")
    _build_caches()


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

    script = ScriptDB.objects.filter(db_key="global_npc_ai").first()
    if not script or script.typeclass_path != "scripts.global_npc_ai.GlobalNPCAI":
        if script:
            script.delete()
        create.create_script("scripts.global_npc_ai.GlobalNPCAI", key="global_npc_ai")

    script = ScriptDB.objects.filter(db_key="area_reset").first()
    if not script or script.typeclass_path != "world.area_reset.AreaReset":
        if script:
            script.delete()
        create.create_script("world.area_reset.AreaReset", key="area_reset")

    # Ensure mob database script exists
    get_mobdb()

    # Ensure all characters are marked tickable for the global ticker
    from typeclasses.characters import Character

    for char in Character.objects.all():
        if not char.tags.has("tickable"):
            char.tags.add("tickable")

    for npc in BaseNPC.objects.all():
        ai_flags = npc.db.actflags or []
        if npc.db.ai_type or ai_flags:
            if not npc.tags.has("npc_ai"):
                npc.tags.add("npc_ai")

    _migrate_experience()
    _backfill_abilities()

    _build_caches()
    ServerConfig.objects.conf("server_start_time", time.time())


def at_server_stop():
    """
    This is called just before the server is shut down, regardless
    of it is for a reload, reset or shutdown.
    """
    logger.log_info("at_server_stop: cleaning up")
    from combat.round_manager import CombatRoundManager
    CombatRoundManager.get().force_end_all_combat()
    _clear_caches()
    ServerConfig.objects.conf("server_start_time", delete=True)


def at_server_reload_start():
    """
    This is called only when server starts back up after a reload.
    """
    logger.log_info("at_server_reload_start: preparing reload")
    ServerConfig.objects.conf("reload_started", time.time())


def at_server_reload_stop():
    """
    This is called only time the server stops before a reload.
    """
    logger.log_info("at_server_reload_stop: reload complete")
    from combat.round_manager import CombatRoundManager
    CombatRoundManager.get().force_end_all_combat()
    ServerConfig.objects.conf("reload_started", delete=True)


def at_server_cold_start():
    """
    This is called only when the server starts "cold", i.e. after a
    shutdown or a reset.
    """
    logger.log_info("at_server_cold_start: cold boot")
    _build_caches()


def at_server_cold_stop():
    """
    This is called only when the server goes down due to a shutdown or
    reset.
    """
    logger.log_info("at_server_cold_stop: shutting down")
    _clear_caches()

