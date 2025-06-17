from dataclasses import dataclass, asdict, field
from typing import List, Dict, Optional

from pathlib import Path
import json
from django.conf import settings
from utils.prototype_manager import load_all_prototypes, save_prototype


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
            rooms=sorted({int(r) for r in data.get("rooms", [])}),
        )

    def to_dict(self) -> Dict:
        data = asdict(self)
        data["rooms"] = sorted({int(r) for r in self.rooms})
        return data


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


def rename_area(old: str, new: str) -> None:
    """Rename area ``old`` to ``new``.

    The area's JSON file is renamed and all room prototypes
    referencing the area are updated.
    """
    idx, area = find_area(old)
    if area is None or idx == -1:
        raise ValueError("Area not found")
    if find_area(new)[1]:
        raise ValueError("Area with that name already exists")

    old_path = _file_path(area.key)
    new_path = _file_path(new)
    if old_path.exists():
        new_path.parent.mkdir(parents=True, exist_ok=True)
        old_path.rename(new_path)

    area.key = new
    save_area(area)

    room_protos = load_all_prototypes("room")
    for vnum, proto in room_protos.items():
        if str(proto.get("area", "")).lower() == old.lower():
            proto["area"] = new
            save_prototype("room", proto, vnum=vnum)


def delete_area(name: str) -> bool:
    """Remove area ``name`` from disk and unassign its rooms.

    The comparison is case-insensitive. Returns ``True`` if an area file
    was removed.
    """
    path = _file_path(name)
    removed = False
    if path.exists():
        path.unlink()
        removed = True

    # clear area from any rooms currently assigned to it
    from evennia.objects.models import ObjectDB
    from typeclasses.rooms import Room

    objs = ObjectDB.objects.filter(db_attributes__db_key="area",
                                   db_attributes__db_strvalue__iexact=name)
    for obj in objs:
        if obj.is_typeclass(Room, exact=False):
            obj.attributes.remove("area")

    return removed


def find_area(name: str) -> tuple[int, Optional[Area]]:
    """Return index and area matching ``name``.

    The search is case-insensitive. If the area is not stored on disk,
    loaded room and NPC prototypes will be scanned for ``area`` fields
    and a temporary :class:`Area` instance constructed if a match is
    found.
    """

    key = name.lower()
    registry, _ = _load_registry()
    for i, data in enumerate(registry):
        area = Area.from_dict(data)
        if area.key.lower() == key:
            return i, area

    # fallback to prototypes
    room_protos = load_all_prototypes("room")
    npc_protos = load_all_prototypes("npc")

    rooms: list[int] = []
    start: int | None = None
    end: int | None = None
    found = False

    for proto in room_protos.values():
        area_name = proto.get("area")
        if not area_name or area_name.lower() != key:
            continue
        found = True
        rid = proto.get("room_id")
        try:
            rid_int = int(rid)
        except (TypeError, ValueError):
            continue
        rooms.append(rid_int)
        if start is None or rid_int < start:
            start = rid_int
        if end is None or rid_int > end:
            end = rid_int

    # also check NPC prototypes for the area name
    if not found:
        for proto in npc_protos.values():
            area_name = proto.get("area")
            if area_name and area_name.lower() == key:
                found = True
                break

    if found:
        area = Area(
            key=name,
            start=start or 0,
            end=end or 0,
            rooms=sorted(set(rooms)),
        )
        return -1, area

    return -1, None


def get_area_vnum_range(name: str) -> Optional[tuple[int, int]]:
    """Return the allowed VNUM range for ``name`` if the area exists."""
    _, area = find_area(name)
    if area:
        return area.start, area.end
    return None


def find_area_by_vnum(vnum: int) -> Area | None:
    """Return the area whose range includes ``vnum``.

    If no registered area covers ``vnum``, room and NPC prototypes are
    searched for a matching ``area`` field. If found, a temporary
    :class:`Area` is returned.
    """

    for area in get_areas():
        if area.start <= vnum <= area.end:
            return area

    room_protos = load_all_prototypes("room")
    npc_protos = load_all_prototypes("npc")

    area_name: str | None = None

    proto = room_protos.get(int(vnum))
    if proto and proto.get("area"):
        area_name = proto.get("area")
    else:
        for p in room_protos.values():
            rid = p.get("room_id")
            try:
                if int(rid) == vnum:
                    area_name = p.get("area")
                    break
            except (TypeError, ValueError):
                continue

    if area_name is None:
        for p in npc_protos.values():
            rid = p.get("vnum")
            try:
                if rid is not None and int(rid) == vnum and p.get("area"):
                    area_name = p.get("area")
                    break
            except (TypeError, ValueError):
                continue

    if area_name:
        _, area = find_area(area_name)
        return area

    return None


def parse_area_identifier(identifier: str) -> Area | None:
    """Return an area by name or numeric index."""

    ident = identifier.strip()
    if ident.isdigit():
        index = int(ident) - 1
        areas = get_areas()
        if 0 <= index < len(areas):
            return areas[index]
        return None
    _, area = find_area(ident)
    return area
