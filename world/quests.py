"""Quest definitions and utilities."""

from dataclasses import dataclass, asdict, field
from typing import Dict, List, Optional

from evennia.server.models import ServerConfig


@dataclass
class Quest:
    """Simple data container for a quest."""

    quest_key: str
    title: str = ""
    goal_type: str = ""
    target: str = ""
    amount: int = 1
    desc: str = ""
    hint: str = ""
    xp_reward: int = 0
    items_reward: List[str] = field(default_factory=list)
    repeatable: bool = False
    level_req: int = 0
    time_limit: int = 0
    start_dialogue: str = ""
    complete_dialogue: str = ""
    failure_dialogue: str = ""
    unique_tag: str = ""
    currency_reward: Dict[str, int] = field(default_factory=dict)
    guild_points: Dict[str, int] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict) -> "Quest":
        return cls(
            quest_key=data.get("quest_key", ""),
            title=data.get("title", ""),
            goal_type=data.get("goal_type", ""),
            target=data.get("target", ""),
            amount=int(data.get("amount", 1)),
            desc=data.get("desc", ""),
            hint=data.get("hint", ""),
            xp_reward=int(data.get("xp_reward", 0)),
            items_reward=data.get("items_reward", []),
            repeatable=bool(data.get("repeatable", False)),
            level_req=int(data.get("level_req", 0)),
            time_limit=int(data.get("time_limit", 0)),
            start_dialogue=data.get("start_dialogue", ""),
            complete_dialogue=data.get("complete_dialogue", ""),
            failure_dialogue=data.get("failure_dialogue", ""),
            unique_tag=data.get("unique_tag", ""),
            currency_reward=data.get("currency_reward", {}),
            guild_points=data.get("guild_points", {}),
        )

    def to_dict(self) -> Dict:
        return asdict(self)


_REGISTRY_KEY = "quest_registry"


def _load_registry() -> List[Dict]:
    return ServerConfig.objects.conf(_REGISTRY_KEY, default=list)


def _save_registry(registry: List[Dict]):
    ServerConfig.objects.conf(_REGISTRY_KEY, value=registry)


def get_quests() -> List[Quest]:
    """Return all stored quests."""
    return [Quest.from_dict(data) for data in _load_registry()]


def save_quest(quest: Quest):
    """Add a new quest to the registry."""
    registry = _load_registry()
    registry.append(quest.to_dict())
    _save_registry(registry)


def update_quest(index: int, quest: Quest):
    """Update quest at index."""
    registry = _load_registry()
    registry[index] = quest.to_dict()
    _save_registry(registry)


def find_quest(key: str) -> tuple[int, Optional[Quest]]:
    """Return index and quest matching key (case-insensitive)."""
    registry = _load_registry()
    for i, data in enumerate(registry):
        quest = Quest.from_dict(data)
        if quest.quest_key.lower() == key.lower():
            return i, quest
    return -1, None


class QuestManager:
    """Helper class for managing quests."""

    @staticmethod
    def all() -> List[Quest]:
        return get_quests()

    @staticmethod
    def save(quest: Quest):
        save_quest(quest)

    @staticmethod
    def update(index: int, quest: Quest):
        update_quest(index, quest)

    @staticmethod
    def find(key: str) -> tuple[int, Optional[Quest]]:
        return find_quest(key)
