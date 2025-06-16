from dataclasses import dataclass, asdict, field
from typing import List, Dict, Optional

from pathlib import Path
import json
from django.conf import settings


@dataclass
class Area:
    """Simple data container for an area."""

    key: str
    start: int
    end: int
    desc: str = ""
    builders: List[str] = field(default_factory=list)
    reset_interval: int = 0
    flags: List[str] = field(default_factory=list)
    age: int = 0
    rooms: List[int] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict) -> "Area":
        return cls(
            key=data.get("key", ""),
            start=int(data.get("start", 0)),
            end=int(data.get("end", 0)),
            desc=data.get("desc", ""),
            builders=data.get("builders", []),
            reset_interval=int(data.get("reset_interval", 0)),
            flags=data.get("flags", []),
            age=int(data.get("age", 0)),
            rooms=[int(r) for r in data.get("rooms", [])],
        )

    def to_dict(self) -> Dict:
        return asdict(self)


_BASE_PATH = Path(settings.GAME_DIR) / "world" / "prototypes" / "areas"


def _file_path(name: str) -> Path:
    """Return path for area ``name``."""
    slug = name.lower().replace(" ", "_")
    return _BASE_PATH / f"{slug}.json"


def _load_registry() -> tuple[List[Dict], List[Path]]:
    """Return list of area dicts and their file paths."""
    areas: List[Dict] = []
    files: List[Path] = []
    if _BASE_PATH.exists():
        for file in sorted(_BASE_PATH.glob("*.json")):
            try:
                with file.open("r") as f:
                    data = json.load(f)
                areas.append(data)
                files.append(file)
            except json.JSONDecodeError:
                continue
    return areas, files


def get_areas() -> List[Area]:
    """Return all stored areas."""
    registry, _ = _load_registry()
    return [Area.from_dict(data) for data in registry]


def save_area(area: Area):
    """Add a new area."""
    _BASE_PATH.mkdir(parents=True, exist_ok=True)
    path = _file_path(area.key)
    with path.open("w") as f:
        json.dump(area.to_dict(), f, indent=4)


def update_area(index: int, area: Area):
    """Update area at ``index``."""
    _, files = _load_registry()
    if 0 <= index < len(files):
        path = files[index]
    else:
        path = _file_path(area.key)
    _BASE_PATH.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        json.dump(area.to_dict(), f, indent=4)


def find_area(name: str) -> tuple[int, Optional[Area]]:
    """Return index and area matching ``name`` (case-insensitive)."""
    registry, _ = _load_registry()
    for i, data in enumerate(registry):
        area = Area.from_dict(data)
        if area.key.lower() == name.lower():
            return i, area
    return -1, None


def get_area_vnum_range(name: str) -> Optional[tuple[int, int]]:
    """Return the allowed VNUM range for ``name`` if the area exists."""
    _, area = find_area(name)
    if area:
        return area.start, area.end
    return None


def find_area_by_vnum(vnum: int) -> Area | None:
    """Return the area whose range includes ``vnum``."""
    for area in get_areas():
        if area.start <= vnum <= area.end:
            return area
    return None


