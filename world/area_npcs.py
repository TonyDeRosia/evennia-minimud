from typing import Dict, List
from evennia.server.models import ServerConfig
from evennia.objects.models import ObjectDB
from typeclasses.npcs import BaseNPC

_REGISTRY_KEY = "area_npc_registry"


def _load_registry() -> Dict[str, List[str]]:
    return ServerConfig.objects.conf(_REGISTRY_KEY, default={})


def _save_registry(registry: Dict[str, List[str]]):
    ServerConfig.objects.conf(_REGISTRY_KEY, value=registry)


def get_area_npc_list(area: str) -> List[str]:
    """Return list of prototype keys for ``area``."""
    return _load_registry().get(area.lower(), [])


def add_area_npc(area: str, proto_key: str):
    """Add ``proto_key`` to ``area`` list."""
    reg = _load_registry()
    key = area.lower()
    lst = reg.setdefault(key, [])
    if proto_key not in lst:
        lst.append(proto_key)
        _save_registry(reg)


def remove_area_npc(area: str, proto_key: str):
    """Remove ``proto_key`` from ``area`` list."""
    reg = _load_registry()
    key = area.lower()
    lst = reg.get(key, [])
    if proto_key in lst:
        lst.remove(proto_key)
        if lst:
            reg[key] = lst
        else:
            reg.pop(key, None)
        _save_registry(reg)


def find_npcs_by_prototype(proto_key: str):
    """Return live NPCs spawned from ``proto_key``."""
    objs = ObjectDB.objects.get_by_attribute(key="prototype_key", value=proto_key)
    return [obj for obj in objs if obj.is_typeclass(BaseNPC, exact=False)]


def find_npcs_by_area(area_tag: str):
    """Return live NPCs with ``db.area_tag`` matching ``area_tag``."""
    objs = ObjectDB.objects.get_by_attribute(key="area_tag", value=area_tag)
    return [obj for obj in objs if obj.is_typeclass(BaseNPC, exact=False)]
