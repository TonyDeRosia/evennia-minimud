"""Achievement definitions and utilities."""

from dataclasses import dataclass, asdict
from typing import Dict, List, Optional

from evennia.server.models import ServerConfig


def normalize_achievement_key(key: str) -> str:
    """Return the canonical achievement key."""
    return str(key).lower().strip()


@dataclass
class Achievement:
    """Simple data container for an achievement."""

    ach_key: str
    title: str = ""
    desc: str = ""
    points: int = 0
    award_msg: str = ""

    @classmethod
    def from_dict(cls, data: Dict) -> "Achievement":
        return cls(
            ach_key=data.get("ach_key", ""),
            title=data.get("title", ""),
            desc=data.get("desc", ""),
            points=int(data.get("points", 0)),
            award_msg=data.get("award_msg", ""),
        )

    def to_dict(self) -> Dict:
        return asdict(self)


_REGISTRY_KEY = "achievement_registry"


def _load_registry() -> List[Dict]:
    return ServerConfig.objects.conf(_REGISTRY_KEY, default=list)


def _save_registry(registry: List[Dict]):
    ServerConfig.objects.conf(_REGISTRY_KEY, value=registry)


def get_achievements() -> List[Achievement]:
    """Return all stored achievements."""
    return [Achievement.from_dict(data) for data in _load_registry()]


def save_achievement(ach: Achievement):
    """Add a new achievement to the registry."""
    registry = _load_registry()
    ach.ach_key = normalize_achievement_key(ach.ach_key)
    registry.append(ach.to_dict())
    _save_registry(registry)


def update_achievement(index: int, ach: Achievement):
    """Update achievement at index."""
    registry = _load_registry()
    ach.ach_key = normalize_achievement_key(ach.ach_key)
    registry[index] = ach.to_dict()
    _save_registry(registry)


def find_achievement(key: str) -> tuple[int, Optional[Achievement]]:
    """Return index and achievement matching key (case-insensitive)."""
    key = normalize_achievement_key(key)
    registry = _load_registry()
    for i, data in enumerate(registry):
        ach = Achievement.from_dict(data)
        if normalize_achievement_key(ach.ach_key) == key:
            return i, ach
    return -1, None


class AchievementManager:
    """Helper class for managing achievements."""

    @staticmethod
    def all() -> List[Achievement]:
        return get_achievements()

    @staticmethod
    def save(achievement: Achievement):
        save_achievement(achievement)

    @staticmethod
    def update(index: int, achievement: Achievement):
        update_achievement(index, achievement)

    @staticmethod
    def find(key: str) -> tuple[int, Optional[Achievement]]:
        return find_achievement(key)
