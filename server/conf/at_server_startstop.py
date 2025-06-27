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

from evennia.server.models import ServerConfig
from evennia.utils import logger

from utils.prototype_manager import load_all_prototypes
from utils.script_utils import get_respawn_manager, resume_paused_scripts

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


def _ensure_room_areas():
    """Assign rooms without area to an appropriate area."""

    from django.conf import settings

    from typeclasses.rooms import Room
    from world.areas import Area, find_area, save_area

    name = getattr(settings, "DEFAULT_AREA_NAME", "midgard")
    start = getattr(settings, "DEFAULT_AREA_START", 200050)
    end = getattr(settings, "DEFAULT_AREA_END", 200150)

    _, area = find_area(name)
    if area is None:
        area = Area(key=name, start=start, end=end)
        save_area(area)

    # Ensure Limbo area exists if Limbo rooms are present
    limbo_area_name = "Limbo"
    idx, limbo_area = find_area(limbo_area_name)

    for room in Room.objects.all():
        if room.db.area:
            continue

        if room.key and room.key.lower() == "limbo":
            if limbo_area is None:
                # create a simple placeholder area for Limbo rooms
                limbo_area = Area(key=limbo_area_name, start=0, end=0)
                save_area(limbo_area)
            room.set_area(limbo_area_name)
        else:
            room.set_area(name)


def at_server_init():
    """Called as the service layer initializes."""

    logger.log_info("at_server_init: building caches")
    _build_caches()


def at_server_start():
    """
    This is called every time the server starts up, regardless of
    how it was shut down.
    """
    from evennia.scripts.models import ScriptDB
    from evennia.utils import create

    from typeclasses.npcs import BaseNPC
    from world.scripts.mob_db import get_mobdb

    script = ScriptDB.objects.filter(db_key="global_tick").first()
    if not script or script.typeclass_path != "typeclasses.scripts.GlobalTick":
        if script:
            script.delete()
        script = create.create_script(
            "typeclasses.scripts.GlobalTick", key="global_tick"
        )
    else:
        if not script.is_active:
            script.start()
        elif getattr(script.db, "_paused_time", None):
            script.unpause()

    script = ScriptDB.objects.filter(db_key="global_npc_ai").first()
    if not script or script.typeclass_path != "scripts.global_npc_ai.GlobalNPCAI":
        if script:
            script.delete()
        script = create.create_script(
            "scripts.global_npc_ai.GlobalNPCAI", key="global_npc_ai"
        )
    else:
        if not script.is_active:
            script.start()
        elif getattr(script.db, "_paused_time", None):
            script.unpause()

    script = ScriptDB.objects.filter(db_key="area_reset").first()
    if not script or script.typeclass_path != "world.area_reset.AreaReset":
        if script:
            script.delete()
        script = create.create_script("world.area_reset.AreaReset", key="area_reset")
    else:
        if not script.is_active:
            script.start()
        elif getattr(script.db, "_paused_time", None):
            script.unpause()

    # remove legacy SpawnManager script if it still exists
    legacy_script = (
        ScriptDB.objects.filter(db_key="spawn_manager").first()
        or ScriptDB.objects.filter(
            typeclass_path="scripts.spawn_manager.SpawnManager"
        ).first()
    )
    if legacy_script:
        logger.log_info("[Startup] Removing legacy SpawnManager script")
        legacy_script.delete()

    spawn_script = get_respawn_manager()
    if (
        not spawn_script
        or spawn_script.typeclass_path
        != "scripts.mob_respawn_manager.MobRespawnManager"
    ):
        if spawn_script:
            spawn_script.delete()
        spawn_script = create.create_script(
            "scripts.mob_respawn_manager.MobRespawnManager",
            key="mob_respawn_manager",
            interval=60,
        )
    else:
        if not spawn_script.is_active:
            spawn_script.start()
        elif getattr(spawn_script.db, "_paused_time", None):
            spawn_script.unpause()

    script = ScriptDB.objects.filter(db_key="corpse_decay").first()
    if not script or script.typeclass_path != "typeclasses.scripts.CorpseDecayManager":
        if script:
            script.delete()
        script = create.create_script(
            "typeclasses.scripts.CorpseDecayManager", key="corpse_decay"
        )
    else:
        if not script.is_active:
            script.start()
        elif getattr(script.db, "_paused_time", None):
            script.unpause()

    if hasattr(spawn_script, "reload_spawns"):
        spawn_script.reload_spawns()

    # Ensure mob database script exists
    get_mobdb()
    from utils.mob_proto import load_npc_prototypes

    load_npc_prototypes()

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

    _build_caches()
    _ensure_room_areas()
    from typeclasses.rooms import Room
    from world.scripts import create_midgard_area

    if not (
        Room.objects.filter(db_tags__db_key__iexact="midgard").exists()
        or Room.objects.filter(
            db_attributes__db_key="area",
            db_attributes__db_strvalue__iexact="midgard",
        ).exists()
    ):
        create_midgard_area.create()
        logger.log_info("Populated Midgard area")
    resume_paused_scripts()
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
