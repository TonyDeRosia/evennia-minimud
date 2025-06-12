"""Game object and NPC prototypes.

This module contains sample prototypes used throughout the game. It also
provides a small registry helper for storing NPC prototypes so they can be
spawned again later via the prototype spawner.
"""

from random import randint, choice

### Crafted prototypes which might be useful to access in other places, such as shops

IRON_DAGGER = {
    "typeclass": "typeclasses.gear.MeleeWeapon",
    "key": "iron dagger",
    "desc": "A keen-edged dagger, made of iron.",
    "tags": [
        ("pierce", "damage_type"),
        ("slash", "damage_type"),
        ("knife", "crafting_tool"),
    ],
    "value": 20,
    "stamina_cost": 3,
    "speed": 3,
    "dmg": 20,
}

IRON_SWORD = {
    "typeclass": "typeclasses.gear.MeleeWeapon",
    "key": "iron sword",
    "desc": "A one-handed sword made of iron.",
    "tags": [("pierce", "damage_type"), ("slash", "damage_type")],
    "value": 30,
    "stamina_cost": 5,
    "speed": 7,
    "dmg": 40,
}

IRON_GREATSWORD = {
    "typeclass": "typeclasses.gear.MeleeWeapon",
    "key": "iron greatsword",
    "desc": "A two-handed iron greatsword.",
    "tags": [
        ("slash", "damage_type"),
        ("bludgeon", "damage_type"),
        ("two_handed", "wielded"),
    ],
    "value": 50,
    "stamina_cost": 10,
    "speed": 12,
    "dmg": 60,
}

IRON_HAUBERK = {
    "typeclass": "typeclasses.objects.ClothingObject",
    "key": "iron hauberk",
    "desc": "A standard iron chainmail tunic.",
    "tags": [
        ("equipment", "flag"),
        ("identified", "flag"),
        ("chest", "slot"),
    ],
    "slot": "chest",
    "armor": 8,
    "value": 20,
    "clothing_type": "chestguard",
}

IRON_CHAUSSES = {
    "typeclass": "typeclasses.objects.ClothingObject",
    "key": "iron chausses",
    "desc": "A pair of mail chausses constructed from iron.",
    "tags": [
        ("equipment", "flag"),
        ("identified", "flag"),
        ("legs", "slot"),
    ],
    "slot": "legs",
    "armor": 8,
    "value": 20,
    "clothing_type": "legguard",
}

LEATHER_BOOTS = {
    "typeclass": "typeclasses.objects.ClothingObject",
    "key": "leather boots",
    "desc": "A sturdy pair of leather boots.",
    "tags": [
        ("equipment", "flag"),
        ("identified", "flag"),
        ("feet", "slot"),
    ],
    "slot": "feet",
    "armor": 1,
    "value": 5,
    "clothing_type": "shoes",
}

SMALL_BAG = {
    "typeclass": "typeclasses.gear.WearableContainer",
    "key": "small bag",
    "desc": "A small leather bag.",
    "capacity": 10,
    "value": 5,
    "clothing_type": "accessory",
}
MEDIUM_BAG = {
    "typeclass": "typeclasses.gear.WearableContainer",
    "key": "medium bag",
    "desc": "A medium leather bag.",
    "capacity": 20,
    "value": 15,
    "clothing_type": "accessory",
}
LARGE_BAG = {
    "typeclass": "typeclasses.gear.WearableContainer",
    "key": "large bag",
    "desc": "A large leather bag.",
    "capacity": 30,
    "value": 30,
    "clothing_type": "accessory",
}

PIE_CRUST = {
    "key": "a pie crust",
    "desc": "A golden brown, but empty, pie crust.",
    "tags": [
        "edible",
    ],
    "stamina": 1,
    "sated": 1,
    "value": 10,
}

### Shop Items

PIE_SLICE = {
    "key": "slice of $choice('apple', 'blueberry', 'peach', 'cherry', 'custard') pie",
    "desc": "A single slice of freshly-baked pie.",
    "tags": [
        "edible",
    ],
    "stamina": 5,
    "sated": 5,
    "value": 5,
}

WOOL_TUNIC = {
    "typeclass": "typeclasses.objects.ClothingObject",
    "key": "$choice('red', 'green', 'blue', 'brown', 'cream') tunic",
    "desc": "A simple, but comfortable, woolen tunic.",
    "tags": [
        ("equipment", "flag"),
        ("identified", "flag"),
        ("chest", "slot"),
    ],
    "slot": "chest",
    "value": 3,
    "clothing_type": "top",
}
WOOL_LEGGINGS = {
    "typeclass": "typeclasses.objects.ClothingObject",
    "key": "$choice('red', 'green', 'blue', 'brown', 'cream') leggings",
    "desc": "A pair of soft and durable woolen leggings.",
    "tags": [
        ("equipment", "flag"),
        ("identified", "flag"),
        ("legs", "slot"),
    ],
    "slot": "legs",
    "value": 3,
    "clothing_type": "legs",
}

### Crafting tools

SMITHING_HAMMER = {
    "key": "smithing hammer",
    "desc": "A sturdy hammer for beating metal.",
    "tags": [("hammer", "crafting_tool")],
    "locks": "get:false()",
}

SMITHING_ANVIL = {
    "key": "anvil",
    "desc": "A typical anvil, which has clearly seen much use.",
    "tags": [("anvil", "crafting_tool")],
    "locks": "get:false()",
}

SMITHING_FURNACE = {
    "key": "furnace",
    "desc": "An active furnace, hot enough to melt down metals.",
    "tags": [("furnace", "crafting_tool")],
    "locks": "get:false()",
}

COOKING_OVEN = {
    "key": "oven",
    "desc": "A cast iron stove - or is it an oven? Well, it's hot and you can cook on it.",
    "tags": [("oven", "crafting_tool"), ("stove", "crafting_tool")],
    "locks": "get:false()",
}


### Materials and their gather nodes

IRON_ORE_NODE = {
    "typeclass": "typeclasses.objects.GatherNode",
    "key": "iron vein",
    "desc": "An outcropping of rocks here appears to contain raw iron.",
    "spawn_proto": "IRON_ORE",
    "gathers": lambda: randint(2, 10),
    "display_priority": "environment",
}
IRON_ORE = {
    "key": "iron ore",
    "desc": "A clump of raw iron ore.",
    "tags": [("iron ore", "crafting_material")],
    "value": 2,
}


COPPER_ORE_NODE = {
    "typeclass": "typeclasses.objects.GatherNode",
    "key": "copper vein",
    "desc": "An outcropping of rocks here appears to contain raw copper.",
    "spawn_proto": "COPPER_ORE",
    "gathers": lambda: randint(2, 10),
    "display_priority": "environment",
}
COPPER_ORE = {
    "key": "copper ore",
    "desc": "A clump of raw copper ore.",
    "tags": [("copper ore", "crafting_material")],
    "value": 1,
}


FRUIT_TREE = {
    "typeclass": "typeclasses.objects.GatherNode",
    "key": "fruit tree",
    "desc": "A tree here is full of fruit, some of which seem to be ripe.",
    "spawn_proto": lambda: choice(("APPLE_FRUIT", "PEAR_FRUIT", "PLUM_FRUIT")),
    "gathers": lambda: randint(5, 10),
    "display_priority": "environment",
}
APPLE_FRUIT = {
    "key": "apple",
    "desc": "A delicious multi-colored apple.",
    "tags": [("apple", "crafting_material"), ("fruit", "crafting_material"), "edible"],
    "stamina": 5,
    "sated": 5,
    "value": 1,
}
PEAR_FRUIT = {
    "key": "pear",
    "desc": "A fragant golden pear.",
    "tags": [("pear", "crafting_material"), ("fruit", "crafting_material"), "edible"],
    "stamina": 5,
    "sated": 5,
    "value": 1,
}
PLUM_FRUIT = {
    "key": "plum",
    "desc": "A large red-black plum.",
    "tags": [("plum", "crafting_material"), ("fruit", "crafting_material"), "edible"],
    "stamina": 5,
    "sated": 5,
    "value": 1,
}


BERRY_BUSH = {
    "typeclass": "typeclasses.objects.GatherNode",
    "key": "berry bush",
    "desc": "A few bushes nearby are covered in berries",
    "spawn_proto": lambda: choice(("BLACKBERRY", "BLUEBERRY", "RASPBERRY")),
    "gathers": lambda: randint(5, 10),
    "display_priority": "environment",
}
BLACKBERRY = {
    "key": "blackberry",
    "desc": "A juicy blackberry.",
    "tags": [
        ("blackberry", "crafting_material"),
        ("berry", "crafting_material"),
        ("fruit", "crafting_material"),
        "edible",
    ],
    "stamina": 1,
    "sated": 1,
    "value": 0,
}
BLUEBERRY = {
    "key": "blueberry",
    "desc": "A single blueberry.",
    "tags": [
        ("blueberry", "crafting_material"),
        ("berry", "crafting_material"),
        ("fruit", "crafting_material"),
        "edible",
    ],
    "stamina": 1,
    "sated": 1,
    "value": 0,
}
RASPBERRY = {
    "key": "raspberry",
    "desc": "A large red raspberry.",
    "tags": [
        ("raspberry", "crafting_material"),
        ("berry", "crafting_material"),
        ("fruit", "crafting_material"),
        "edible",
    ],
    "stamina": 1,
    "sated": 1,
    "value": 0,
}


LUMBER_TREE = {
    "typeclass": "typeclasses.objects.GatherNode",
    "key": "$choice('pine', 'oak', 'ash') tree",
    "desc": "This tree looks like a great source of lumber.",
    "spawn_proto": "WOOD_LOG",
    "gathers": lambda: randint(2, 10),
    "display_priority": "environment",
}
WOOD_LOG = {
    "key": "log of wood",
    "desc": "A decent-sized wooden log. Not so big you can't carry it.",
    "tags": [
        ("wood", "crafting_material"),
    ],
    "value": 1,
}


DRIFTWOOD = {
    "typeclass": "typeclasses.objects.GatherNode",
    "key": "pile of driftwood",
    "desc": "Some of this wood looks like it would be useful.",
    "spawn_proto": "WOOD_LOG",
    "gathers": lambda: randint(1, 3),
    "display_priority": "environment",
}


### Mobs

ANGRY_BEAR = {
    "typeclass": "typeclasses.characters.NPC",
    "key": "a large angry bear",
    "desc": "A large brown bear. It really doesn't like you!",
    "gender": "neutral",
    "react_as": "aggressive",
    "flee_at": 5,
    "armor": 20,
    "name_color": "r",
    "STR": 15,
    "natural_weapon": {
        "name": "claws",
        "damage_type": "slash",
        "damage": 10,
        "speed": 8,
        "stamina_cost": 10,
    },
    "exp_reward": 10,
    # randomly generate a list of drop prototype keys when the mob is spawned
    "drops": lambda: ["RAW_MEAT"] * randint(3, 5) + ["ANIMAL_HIDE"] * randint(0, 5),
    "can_attack": True,
}

COUGAR = {
    "typeclass": "typeclasses.characters.NPC",
    "key": "a mountain lion",
    "desc": "A sleek mountain lion. It doesn't appreciate you invading its territory. At all.",
    "gender": "neutral",
    "react_as": "aggressive",
    "flee_at": 15,
    "armor": 15,
    "name_color": "r",
    "STR": 8,
    "DEX": 15,
    "natural_weapon": {
        "name": "claws",
        "damage_type": "slash",
        "damage": 10,
        "speed": 8,
        "stamina_cost": 10,
    },
    "exp_reward": 10,
    # randomly generate a list of drop prototype keys when the mob is spawned
    "drops": lambda: ["RAW_MEAT"] * randint(0, 3) + ["ANIMAL_HIDE"] * randint(0, 2),
    "can_attack": True,
}

SQUIRREL = {
    "typeclass": "typeclasses.characters.NPC",
    "key": "a $choice('grey', 'brown') squirrel",
    "desc": "Look! A squirrel!",
    "react_as": "timid",
    "gender": "neutral",
    "drops": lambda: ["RAW_MEAT"] * randint(0, 1),
    "can_attack": True,
}

PHEASANT = {
    "typeclass": "typeclasses.characters.NPC",
    "key": "a pheasant",
    "desc": "A healthy wild pheasant.",
    "react_as": "timid",
    "gender": "neutral",
    "drops": lambda: ["RAW_MEAT"] * randint(0, 1),
    "can_attack": True,
}

DOE_DEER = {
    "typeclass": "typeclasses.characters.NPC",
    "key": "a doe",
    "desc": "A skittish doe with large brown eyes.",
    "gender": "female",
    "react_as": "timid",
    "armor": 10,
    "DEX": 15,
    "can_attack": True,
    # randomly generate a list of drop prototype keys when the mob is spawned
    "drops": lambda: ["DEER_MEAT"] * randint(1, 3) + ["ANIMAL_HIDE"] * randint(0, 3),
}

STAG_DEER = {
    "typeclass": "typeclasses.characters.NPC",
    "key": "a stag",
    "desc": "A wary adult stag, sporting a full rack of antlers.",
    "gender": "male",
    "armor": 10,
    "DEX": 15,
    "natural_weapon": {
        "name": "antlers",
        "damage_type": "pierce",
        "damage": 10,
        "speed": 10,
        "stamina_cost": 5,
    },
    # randomly generate a list of drop prototype keys when the mob is spawned
    "drops": lambda: ["DEER_MEAT"] * randint(1, 3)
    + ["DEER_ANTLER"] * randint(0, 2)
    + ["ANIMAL_HIDE"] * randint(0, 3),
    "exp_reward": 10,
    "can_attack": True,
}

# Example NPC used for development testing
TEST_BLACKSMITH = {
    "typeclass": "typeclasses.characters.NPC",
    "key": "test blacksmith",
    "desc": "A sturdy blacksmith created for testing purposes.",
    "gender": "male",
    "can_attack": False,
}

### Mob drops

RAW_MEAT = {
    "key": "raw meat",
    "desc": "A piece of meat from an animal. It hasn't been cooked.",
    "tags": [("raw meat", "crafting_material")],
}
ANIMAL_HIDE = {
    "key": "animal hide",
    "desc": "A section of hide from an animal, suitable for leather-crafting",
    "tags": [("leather", "crafting_material")],
}
DEER_MEAT = {
    "key": "raw deer meat",
    "desc": "A piece of meat from a deer. It hasn't been cooked.",
    "tags": [("raw meat", "crafting_material"), ("venison", "crafting_material")],
}
DEER_ANTLER = {
    "key": "antler",
    "desc": "A forked antler bone from an adult stag.",
    "tags": [
        ("bone", "crafting_material"),
    ],
}

# Example loot table entry structure. A loot table is stored on
# ``npc.db.loot_table`` as a list of mappings with the prototype key and the
# percent chance to drop that prototype when the NPC dies.
# Example::
#
#     [{"proto": "RAW_MEAT", "chance": 50}, {"proto": "ANIMAL_HIDE", "chance": 25, "guaranteed_after": 5}]

EXAMPLE_LOOT_TABLE = [{"proto": "RAW_MEAT", "chance": 50}]

# ------------------------------------------------------------
# NPC prototype registry utilities
# ------------------------------------------------------------

from typing import Dict, Optional
import json
from pathlib import Path
from django.conf import settings


def _npc_proto_file() -> Path:
    """Return the path to the NPC prototype JSON file."""
    return Path(settings.PROTOTYPE_NPC_FILE)


def _load_npc_registry() -> Dict[str, dict]:
    """Return the stored NPC prototypes from the JSON file."""
    try:
        with _npc_proto_file().open("r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError:
        return {}


_ALIAS_MAP = {
    "sex": "gender",
    "coins": "coin_drop",
    "xp_reward": "exp_reward",
    "resists": "resistances",
}


def _normalize_proto(proto: dict) -> None:
    """Convert legacy keys in ``proto`` to current names."""
    for old, new in _ALIAS_MAP.items():
        if old in proto and new not in proto:
            proto[new] = proto[old]

    proto.setdefault("npc_type", "base")
    proto.setdefault("race", "human")
    proto.setdefault("level", 1)
    proto.setdefault("damage", 1)


def _save_npc_registry(registry: Dict[str, dict]):
    path = _npc_proto_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        json.dump(registry, f, indent=4)


def get_npc_prototypes(filter_by: Optional[dict] = None) -> Dict[str, dict]:
    """Return registered NPC prototypes optionally filtered by criteria.

    Args:
        filter_by (dict, optional): Mapping of filters. Supported keys are
            ``"class"``, ``"race"``, ``"role"``, ``"tag"`` and ``"zone"``.

    Returns:
        dict: Mapping of prototype key -> prototype data.
    """

    registry = _load_npc_registry()
    for proto in registry.values():
        _normalize_proto(proto)
        if "role" not in proto and proto.get("npc_type"):
            proto["role"] = proto["npc_type"]
    if not filter_by:
        return registry

    result: Dict[str, dict] = {}
    for key, proto in registry.items():
        if "class" in filter_by and proto.get("npc_type") != filter_by["class"]:
            continue
        if "race" in filter_by and proto.get("race") != filter_by["race"]:
            continue
        if "role" in filter_by:
            roles = proto.get("roles") or []
            if isinstance(roles, str):
                roles = [roles]
            if not roles and proto.get("npc_type"):
                roles = [proto.get("npc_type")]
            if filter_by["role"] not in roles:
                continue
        if "tag" in filter_by:
            tag = filter_by["tag"]
            tags = proto.get("tags") or []

            def _tag_match(entry):
                if isinstance(entry, (list, tuple)):
                    return entry and entry[0] == tag
                return entry == tag

            if not any(_tag_match(t) for t in tags):
                continue
        if "zone" in filter_by:
            zone = filter_by["zone"]
            tags = proto.get("tags") or []

            def _zone_match(entry):
                if isinstance(entry, (list, tuple)):
                    return entry and entry[0] == zone and (
                        len(entry) == 1 or entry[1] in {"zone", "area"}
                    )
                return False

            if not any(_zone_match(t) for t in tags):
                continue
        result[key] = proto

    return result


def register_npc_prototype(key: str, prototype: dict):
    """Save ``prototype`` under ``key`` in the persistent registry."""
    registry = _load_npc_registry()
    _normalize_proto(prototype)
    registry[key] = prototype
    _save_npc_registry(registry)


def filter_npc_prototypes(protos: dict, filters: dict) -> list[tuple[str, dict]]:
    """Return ``protos`` entries matching ``filters``.

    Args:
        protos (dict): Mapping of key -> prototype data.
        filters (dict): Filters to apply. Supported keys are ``"class"``,
            ``"race"``, ``"role"`` and ``"tag"``.

    Returns:
        list[tuple[str, dict]]: Sequence of ``(key, prototype)`` pairs that
        matched all filters.
    """

    if not filters:
        return list(protos.items())

    result: list[tuple[str, dict]] = []
    for key, proto in protos.items():
        if "class" in filters and proto.get("npc_type") != filters["class"]:
            continue
        if "race" in filters and proto.get("race") != filters["race"]:
            continue
        if "role" in filters:
            roles = proto.get("roles") or []
            if isinstance(roles, str):
                roles = [roles]
            if not roles and proto.get("npc_type"):
                roles = [proto.get("npc_type")]
            if filters["role"] not in roles:
                continue
        if "tag" in filters:
            tag = filters["tag"]
            tags = proto.get("tags") or []

            def _tag_match(entry):
                if isinstance(entry, (list, tuple)):
                    return entry and entry[0] == tag
                return entry == tag

            if not any(_tag_match(t) for t in tags):
                continue
        result.append((key, proto))

    return result
