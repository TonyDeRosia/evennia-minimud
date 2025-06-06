VALID_SLOTS = {
    "mainhand",
    "offhand",
    "mainhand/offhand",
    "twohanded",
    "head",
    "neck",
    "shoulders",
    "chest",
    "cloak",
    "wrists",
    "hands",
    "ring1",
    "ring2",
    "tabard",
    "waist",
    "legs",
    "feet",
    "accessory",
    "trinket",
}

# Maps common slot synonyms to their canonical counterparts.
SLOT_MAP = {
    "helm": "head",
    "helmet": "head",
    "hat": "head",
    "amulet": "neck",
    "necklace": "neck",
    "pendant": "neck",
    "belt": "waist",
    "boots": "feet",
    "gloves": "hands",
    "bracelet": "wrists",
    "ring": "ring1",
}


def normalize_slot(name):
    """Return the canonical slot name for ``name``."""

    if not name:
        return None

    name = name.lower().strip()

    # return canonical slot if already valid
    if name in VALID_SLOTS:
        return name

    # look up alias
    return SLOT_MAP.get(name)

