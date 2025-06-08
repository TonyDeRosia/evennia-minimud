from typing import Dict, List
from evennia.server.models import ServerConfig

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
