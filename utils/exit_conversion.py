from evennia.objects.models import ObjectDB


def convert_exits():
    """Convert all exit objects into room.db.exits mappings."""
    exits = ObjectDB.objects.filter(db_destination__isnull=False)
    for ex in exits:
        src = ex.location
        dst = ex.db_destination
        if not src or not dst:
            continue
        mapping = src.attributes.get("exits", default={})
        if ex.db.wilderness_name and ex.db.wilderness_coords:
            mapping[ex.key] = {
                "wilderness_name": ex.db.wilderness_name,
                "wilderness_coords": ex.db.wilderness_coords,
            }
        else:
            mapping[ex.key] = dst
        src.db.exits = mapping
        ex.delete()

