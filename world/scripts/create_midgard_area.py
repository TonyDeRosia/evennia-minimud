from evennia import create_object
from evennia.objects.models import ObjectDB
from evennia.utils import logger
from typeclasses.rooms import Room
from utils.prototype_manager import load_all_prototypes


def create():
    """Instantiate Midgard rooms and their exits if missing."""
    prototypes = load_all_prototypes("room")
    midgard = [p for p in prototypes.values() if p.get("area") == "midgard"]
    rooms = {}
    created_rooms = 0
    for proto in midgard:
        vnum = int(proto.get("room_id"))
        objs = ObjectDB.objects.filter(
            db_attributes__db_key="room_id", db_attributes__db_value=vnum
        )
        room_obj = None
        for obj in objs:
            if obj.is_typeclass(Room, exact=False):
                room_obj = obj
                break
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
        created_rooms += 1
    # create exits
    created_exits = 0
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
                created_exits += 1

    summary = f"Created {created_rooms} rooms and {created_exits} exits."
    logger.log_info(summary)
    return summary

