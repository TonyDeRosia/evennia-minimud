from __future__ import annotations

"""Utility functions for creating and populating corpses."""

from random import randint
from django.conf import settings
from evennia import create_object
from evennia.utils import inherits_from, logger
from evennia.prototypes.spawner import spawn

from utils.currency import to_copper, from_copper, format_wallet
from world.mob_constants import BODYPARTS, ACTFLAGS


__all__ = [
    "make_corpse",
    "create_corpse",
    "apply_loot",
    "finalize_corpse",
]


def make_corpse(npc):
    """Create and populate a corpse object for ``npc``."""
    if not npc or not npc.location:
        return None

    existing = [
        obj
        for obj in npc.location.contents
        if obj.is_typeclass("typeclasses.objects.Corpse", exact=False)
        and obj.db.corpse_of_id == npc.dbref
    ]
    if existing:
        return existing[0]

    decay = getattr(npc.db, "corpse_decay_time", None)
    if decay is None:
        decay = randint(
            getattr(settings, "CORPSE_DECAY_MIN", 5),
            getattr(settings, "CORPSE_DECAY_MAX", 10),
        )

    attrs = [
        ("corpse_of", npc.key),
        ("corpse_of_id", npc.dbref),
        ("is_corpse", True),
        ("decay_time", decay),
    ]
    if getattr(npc.db, "vnum", None) is not None:
        attrs.append(("npc_vnum", npc.db.vnum))

    corpse = create_object(
        "typeclasses.objects.Corpse",
        key=f"corpse of {npc.key}",
        location=npc.location,
        attributes=attrs,
    )

    no_loot = ACTFLAGS.NOLOOT.value in (npc.db.actflags or [])
    if not no_loot:
        for obj in list(npc.contents):
            obj.location = corpse

        moved = set()
        if hasattr(npc, "equipment"):
            for item in npc.equipment.values():
                if item and item not in moved:
                    item.location = corpse
                    moved.add(item)

        if npc.db.coin_drop:
            for coin, amt in npc.db.coin_drop.items():
                if int(amt):
                    pile = create_object(
                        "typeclasses.objects.CoinPile",
                        key=f"{coin} coins",
                        location=corpse,
                    )
                    pile.db.coin_type = coin
                    pile.db.amount = int(amt)

    corpse.db.desc = f"The corpse of {npc.key} lies here."

    return corpse


def create_corpse(victim):
    """Create and return a corpse for ``victim``."""
    if not victim:
        return None
    return make_corpse(victim)


def apply_loot(victim, corpse, killer=None):
    """Generate additional loot for ``victim``."""
    if not victim or not corpse:
        return

    actflags = getattr(victim.db, "actflags", []) or []
    no_loot = "noloot" in [str(f).lower() for f in actflags]

    if inherits_from(victim, "typeclasses.characters.PlayerCharacter"):
        # spawn random body parts
        from world import prototypes

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
        return

    if inherits_from(victim, "typeclasses.characters.NPC"):
        drops, coin_loot = victim.drop_loot(killer)
        objs = spawn(*drops)
        for obj in objs:
            if not obj:
                logger.log_warn(f"Loot drop for {victim} returned no object.")
                continue
            obj.move_to(corpse, quiet=True)

        coin_map = {}
        if victim.db.coin_drop:
            for coin, amt in (victim.db.coin_drop or {}).items():
                coin_map[coin] = coin_map.get(coin, 0) + int(amt)
        for coin, amt in coin_loot.items():
            coin_map[coin] = coin_map.get(coin, 0) + int(amt)

        if coin_map:
            total_copper = to_copper(coin_map)
            if killer:
                wallet = killer.db.coins or {}
                killer.db.coins = from_copper(to_copper(wallet) + total_copper)
                if hasattr(killer, "msg"):
                    coins = format_wallet(from_copper(total_copper))
                    killer.msg(f"You receive |Y{coins}|n.")
            else:
                for coin, amt in from_copper(total_copper).items():
                    if amt:
                        pile = create_object(
                            "typeclasses.objects.CoinPile",
                            key=f"{coin} coins",
                            location=corpse,
                        )
                        pile.db.coin_type = coin
                        pile.db.amount = amt


def finalize_corpse(victim, corpse):
    """Apply final attributes after loot has been moved."""
    if not victim or not corpse:
        return

    if getattr(victim, "key", None):
        corpse.db.corpse_of = victim.key
    if getattr(victim, "dbref", None):
        corpse.db.corpse_of_id = victim.dbref
    if getattr(getattr(victim, "db", None), "vnum", None) is not None:
        corpse.db.npc_vnum = victim.db.vnum
    if getattr(victim.db, "weight", None) is not None:
        corpse.db.weight = victim.db.weight
    corpse.db.desc = f"The corpse of {victim.key} lies here."

