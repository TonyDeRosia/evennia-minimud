from dataclasses import dataclass, asdict
from typing import List, Dict

from evennia.server.models import ServerConfig


@dataclass
class Area:
    """Simple data container for an area."""

    key: str
    start: int
    end: int
    desc: str = ""

    @classmethod
    def from_dict(cls, data: Dict) -> "Area":
        return cls(
            key=data.get("key", ""),
            start=int(data.get("start", 0)),
            end=int(data.get("end", 0)),
            desc=data.get("desc", ""),
        )

    def to_dict(self) -> Dict:
        return asdict(self)


_REGISTRY_KEY = "area_registry"


def _load_registry() -> List[Dict]:
    return ServerConfig.objects.conf(_REGISTRY_KEY, default=list)


def _save_registry(registry: List[Dict]):
    ServerConfig.objects.conf(_REGISTRY_KEY, value=registry)


def get_areas() -> List[Area]:
    """Return all stored areas."""
    return [Area.from_dict(data) for data in _load_registry()]


def save_area(area: Area):
    """Add a new area to the registry."""
    registry = _load_registry()
    registry.append(area.to_dict())
    _save_registry(registry)


def update_area(index: int, area: Area):
    """Update area at index."""
    registry = _load_registry()
    registry[index] = area.to_dict()
    _save_registry(registry)


def find_area(name: str) -> tuple[int, Optional[Area]]:
    """Return index and area matching name (case-insensitive)."""
    registry = _load_registry()
    for i, data in enumerate(registry):
        area = Area.from_dict(data)
        if area.key.lower() == name.lower():
            return i, area
    return -1, None


