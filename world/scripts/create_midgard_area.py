from evennia import create_object
from evennia.objects.models import ObjectDB
from evennia.utils import logger
from typeclasses.rooms import Room
from utils.prototype_manager import load_all_prototypes


def create() -> tuple[int, int]:
    """
    Instantiate Midgard rooms and their exits if missing.

    Returns
    -------
    tuple[int, int]
        Number of rooms created and exits created.
    """
    prototypes = load_all_prototypes("room")
    midgard = [p for p in prototypes.values() if p.get("area") == "midgard"]

    rooms = {}
    rooms_created = 0

    for proto in midgard:
        vnum = int(proto.get("room_id"))
        objs = ObjectDB.objects.filter(
            db_attributes__db_key="room_id", db_attributes__db_value=vnum
        )
        room_obj = next((obj for obj in objs if obj.is_typeclass(Room, exact=False)), None)

        if room_obj:
            rooms[vnum] = room_obj
            continue

        obj = create_object(
            proto.get("typeclass", Room), key=proto.get("key"), nohome=True
        )
        obj.db.desc = proto.get("desc", "")
        obj.db.room_id = vnum
        obj.db.area = proto.get("area")

        if proto.get("xyz"):
            obj.db.xyz = proto["xyz"]

        for tag in proto.get("tags", []):
            if isinstance(tag, (list, tuple)) and len(tag) >= 1:
                name = tag[0]
                category = tag[1] if len(tag) > 1 else None
                obj.tags.add(name, category=category)
            else:
                obj.tags.add(tag)

        rooms[vnum] = obj
        rooms_created += 1

    exits_created = 0
    for proto in midgard:
        vnum = int(proto.get("room_id"))
        room = rooms.get(vnum)
        if not room:
            continue
        for dir_name, dest_vnum in proto.get("exits", {}).items():
            dest = rooms.get(int(dest_vnum))
            if not dest:
                continue
            room.db.exits = room.db.exits or {}
            if dir_name not in room.db.exits:
                room.db.exits[dir_name] = dest
                exits_created += 1

    logger.log_info(f"✅ Midgard created: {rooms_created} rooms, {exits_created} exits.")
    return rooms_created, exits_created
