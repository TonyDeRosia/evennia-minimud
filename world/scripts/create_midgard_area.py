from evennia import create_object, search_object
from typeclasses.rooms import Room
from typeclasses.exits import Exit
from utils.prototype_manager import load_all_prototypes


def create():
    """Instantiate Midgard rooms and their exits if missing."""
    prototypes = load_all_prototypes("room")
    midgard = [p for p in prototypes.values() if p.get("area") == "midgard"]
    rooms = {}
    for proto in midgard:
        vnum = int(proto.get("room_id"))
        if search_object(f"#{vnum}"):
            rooms[vnum] = search_object(f"#{vnum}")[0]
            continue
        obj = create_object(proto.get("typeclass", Room), key=proto.get("key"))
        obj.db.desc = proto.get("desc", "")
        obj.db.vnum = vnum
        obj.db.area = proto.get("area")
        if proto.get("xyz"):
            obj.db.xyz = proto["xyz"]
        rooms[vnum] = obj
    # create exits
    for proto in midgard:
        vnum = int(proto.get("room_id"))
        room = rooms.get(vnum)
        if not room:
            continue
        for dir_name, dest_vnum in proto.get("exits", {}).items():
            dest = rooms.get(int(dest_vnum))
            if not dest:
                continue
            if not room.exits.get(dir_name):
                create_object(Exit, key=dir_name, location=room, destination=dest)

