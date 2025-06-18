"""Utility to wipe all areas except Midgard and Verdant Overgrowth."""

from evennia.objects.models import ObjectDB

AREAS_TO_KEEP = {"midgard", "verdant_overgrowth"}

all_rooms = ObjectDB.objects.filter(db_tags__db_category="area")

deleted_areas: set[str] = set()
exits_deleted = 0

for room in all_rooms:
    area_tag = next((tag.db_key for tag in room.tags.all() if tag.category == "area"), None)

    if not area_tag or not room.is_typeclass("typeclasses.rooms.Room", exact=False):
        continue

    if area_tag not in AREAS_TO_KEEP:
        deleted_areas.add(area_tag)
        room.delete()
        continue

    for exit_obj in list(room.exits):
        exit_obj.delete()
        exits_deleted += 1
    room.db.exits = {}

print("✅ Cleanup complete.")
print(f"- Deleted areas: {', '.join(sorted(deleted_areas)) or 'None'}")
print(f"- Exits deleted in kept areas: {exits_deleted}")
