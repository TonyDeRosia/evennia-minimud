from random import randint
from evennia.utils import logger, inherits_from
from utils.mob_utils import make_corpse
from utils.debug import admin_debug

from evennia.prototypes.spawner import spawn
from evennia import create_object


def spawn_corpse(char, killer=None):
    """Create and return a corpse for ``char``.

    Player characters receive random body part objects while NPCs
    trigger their loot handling via ``drop_loot``.
    """
    admin_debug(f"Spawning corpse for {getattr(char, 'key', char)}")
    corpse = make_corpse(char)
    if not corpse:
        return None

    from typeclasses.characters import PlayerCharacter, NPC
    if inherits_from(char, PlayerCharacter):
        from world import prototypes
        from world.mob_constants import BODYPARTS

        for part in BODYPARTS:
            if randint(1, 100) <= 50:
                proto = getattr(prototypes, f"{part.name}_PART", None)
                if proto:
                    spawned = spawn(proto)[0]
                    spawned.location = corpse
                else:
                    create_object(
                        "typeclasses.objects.Object",
                        key=part.value,
                        location=corpse,
                    )
        return corpse

    if inherits_from(char, NPC):
        try:
            admin_debug(f"{getattr(char, 'key', char)} dropping loot")
            corpse = char.drop_loot(killer)
        except Exception as err:  # pragma: no cover - log errors
            logger.log_err(f"Loot drop error on {char}: {err}")
        return corpse

    return corpse
