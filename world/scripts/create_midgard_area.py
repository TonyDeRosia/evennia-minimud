from evennia import create_object
from evennia.objects.models import ObjectDB
from evennia.utils import logger

midgard_rooms = {
    200050: {
        "name": "|cTemple Steppes|n",
        "desc": (
            "Wide marble steps rise toward an ancient temple crowned with golden spires. "
            "Weathered pillars etched with celestial symbols surround the area, glowing faintly with divine energy. "
            "A soft breeze stirs the incense drifting from the temple entrance, filling the air with a sense of calm and purpose. "
            "This sacred hub stands as the beating heart of Midgard, where adventurers come to seek clarity and divine guidance."
        ),
        "exits": {"south": 200051},
    },
    200051: {
        "name": "|wPath to Temple|n",
        "desc": (
            "Stone lanterns guide your descent along a cobbled trail that winds between statues of forgotten gods. "
            "Faint chanting echoes from above, lingering like memory in the air. "
            "The scent of flowers and incense fades the farther you walk from the temple. "
            "This tranquil path serves as a bridge between Midgard’s divine heights and its bustling town below."
        ),
        "exits": {"north": 200050, "south": 200052},
    },
    200052: {
        "name": "|GMidgard Square|n",
        "desc": (
            "The town square bustles with merchants and lively chatter. "
            "Colorful stalls ring a central fountain splashing gently. "
            "The smell of fresh bread mixes with the clang of distant forges. "
            "Travelers from all paths pause here before continuing their journeys."
        ),
        "exits": {"north": 200051, "east": 200053},
    },
    200053: {
        "name": "|yEast Market|n",
        "desc": (
            "Vendors shout prices from ramshackle booths lining the street. "
            "Bright awnings flap in the ever-present breeze. "
            "Coins clink and children laugh as trade carries on. "
            "The eastern road leads deeper into Midgard’s busy districts."
        ),
        "exits": {"west": 200052, "south": 200054},
    },
    200054: {
        "name": "|mGuildhall Entrance|n",
        "desc": (
            "Carved stone arches mark the entrance to the grand guildhall. "
            "Banners of various colors flutter proudly from the walls. "
            "Footsteps echo softly beneath the high ceilings. "
            "New members often gather here before pledging their service."
        ),
        "exits": {"north": 200053, "west": 200055},
    },
    200055: {
        "name": "|cKnight Quarters|n",
        "desc": (
            "Rows of polished armor stand at attention along the corridor. "
            "The scent of oil and metal lingers in the air. "
            "Trophies from past campaigns adorn the walls with pride. "
            "Off-duty knights swap stories here after their patrols."
        ),
        "exits": {"east": 200054},
    },
    200056: {
        "name": "|wTraining Yard|n",
        "desc": (
            "Wooden dummies and targets crowd the open yard. "
            "Instructors bark orders to squires going through drills. "
            "Sweat and determination hang thick in the afternoon sun. "
            "The clatter of weapons rings out from dawn until dusk."
        ),
        "exits": {},
    },
    200057: {
        "name": "|rBarracks Path|n",
        "desc": (
            "A narrow lane runs between sturdy stone barracks. "
            "Booted soldiers march in step to a silent cadence. "
            "Flags bearing Midgard’s sigil snap crisply overhead. "
            "The lane continues south toward the outer gate."
        ),
        "exits": {"west": 200056, "south": 200058},
    },
    200058: {
        "name": "|gSouth Gate|n",
        "desc": (
            "Heavy iron gates guard the southern exit of the town. "
            "Beyond lies a well-worn road fading into the countryside. "
            "Guards nod to those leaving on errands or patrol. "
            "This threshold marks the boundary between Midgard and the wider world."
        ),
        "exits": {"north": 200057},
    },
    200059: {
        "name": "|GForge Square|n",
        "desc": (
            "The clang of hammer on anvil resonates throughout this square. "
            "Sparks fly as smiths labor over glowing metal. "
            "The air is thick with smoke and the smell of coal. "
            "Apprentices hurry about carrying fresh supplies."
        ),
        "exits": {"east": 200060},
    },
    200060: {
        "name": "|CSmithy|n",
        "desc": (
            "Inside the smithy, heat from the forge creates shimmering waves. "
            "Tools hang neatly from racks awaiting the smith’s hand. "
            "Finished blades glint faintly in the low light. "
            "A door to the north leads up to the watchtower above."
        ),
        "exits": {"west": 200059},
    },
    200061: {
        "name": "|YWatchtower|n",
        "desc": (
            "This tall tower commands a view of the surrounding lands. "
            "Stairs spiral upward toward a lookout platform. "
            "Torches burn steadily, warding off the creeping dark. "
            "From here the town’s defenders keep watch through the night."
        ),
        "exits": {},
    },
}


def create() -> tuple[int, int]:
    """
    Instantiate Midgard rooms and their exits if missing.

    Returns
    -------
    tuple[int, int]
        Number of rooms created and exits created.
    """
    from typeclasses.rooms import Room
    from typeclasses.exits import Exit

    rooms: dict[int, Room] = {}
    rooms_created = 0

    for vnum, data in midgard_rooms.items():
        objs = ObjectDB.objects.filter(
            db_attributes__db_key="room_id", db_attributes__db_value=vnum
        )
        room = next((obj for obj in objs if obj.is_typeclass(Room, exact=False)), None)
        if not room:
            room = create_object(Room, key=data["name"])
            rooms_created += 1

        room.key = data["name"]
        room.db.room_id = vnum
        room.db.desc = data.get("desc", "")
        room.tags.add("midgard", category="area")

        rooms[vnum] = room

    exits_created = 0
    for vnum, data in midgard_rooms.items():
        src = rooms.get(vnum)
        if not src:
            continue

        exits = src.db.exits or {}

        for dir_name, dest_vnum in data.get("exits", {}).items():
            dest = rooms.get(dest_vnum)
            if not dest:
                continue

            if exits.get(dir_name) != dest:
                exits[dir_name] = dest

            exists = any(
                ex.key.lower() == dir_name.lower() and ex.destination == dest
                for ex in src.exits
            )
            if not exists:
                create_object(
                    "typeclasses.exits.Exit",
                    key=dir_name,
                    location=src,
                    destination=dest,
                )
                exits_created += 1

        src.db.exits = exits

    logger.log_info(
        f"✅ Midgard created: {rooms_created} rooms, {exits_created} exits."
    )
    return rooms_created, exits_created
