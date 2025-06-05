"""
Chargen Menu - Finalized Character Creation Menu

Flow: race → class → gender → stat allocation → name → description → confirm
"""

from evennia import create_object
from evennia.utils import dedent
from typeclasses.characters import PlayerCharacter, Character
from world.scripts import races, classes
from world.stats import CORE_STAT_KEYS, apply_stats

STAT_LIST = CORE_STAT_KEYS
STAT_POINTS = 24

# ---------------- Welcome ----------------

def menunode_welcome(caller):
    """Starting point of chargen."""
    if not hasattr(caller, "ndb"):
        caller.ndb = {}

    if not caller.ndb.new_char:
        new_char = create_object(PlayerCharacter, key="In Progress", location=None)
        caller.ndb.new_char = new_char
    else:
        new_char = caller.ndb.new_char

    if not new_char.is_typeclass("typeclasses.characters.PlayerCharacter", exact=False):
        new_char.swap_typeclass("typeclasses.characters.PlayerCharacter", clean_attributes=False)

    text = dedent("""
        |wWelcome to Relics and Reckoning!|n

        Let's begin creating your character:
        - Choose your race
        - Choose your class
        - Choose your gender
        - Allocate your stats
        - Set your name and description

        |yReady?|n
    """)
    options = [{"desc": "Begin!", "goto": "menunode_choose_race"}]
    return text, options

# ---------------- Race ----------------

def menunode_choose_race(caller):
    text = "|wChoose Your Race|n\n"
    options = []
    for entry in races.RACE_LIST:
        options.append({
            "desc": f"{entry['name']} - {entry['desc']}",
            "goto": (_set_race, {"race": entry["name"]})
        })
    return text, options

def _set_race(caller, raw_string, race, **kwargs):
    char = caller.ndb.new_char
    char.db.race = race
    char.db.charclass = None
    for stat in STAT_LIST:
        # store base values using AttributeHandler or db assignment
        char.attributes.add(stat.lower(), 0)
    return "menunode_choose_class"

# ---------------- Class ----------------

def menunode_choose_class(caller):
    text = "|wChoose Your Class|n\n"
    options = []
    for entry in classes.CLASS_LIST:
        options.append({
            "desc": f"{entry['name']} - {entry['desc']}",
            "goto": (_set_class, {"charclass": entry["name"]})
        })
    options.append({"desc": "Back", "goto": "menunode_choose_race"})
    return text, options

def _set_class(caller, raw_string, charclass, **kwargs):
    caller.ndb.new_char.db.charclass = charclass
    _apply_base_stats(caller)
    return "menunode_choose_gender"

def _apply_base_stats(caller):
    char = caller.ndb.new_char
    race_mods = next((r["stat_mods"] for r in races.RACE_LIST if r["name"] == char.db.race), {})
    class_mods = next((c["stat_mods"] for c in classes.CLASS_LIST if c["name"] == char.db.charclass), {})
    for stat in STAT_LIST:
        base = race_mods.get(stat, 0) + class_mods.get(stat, 0)
        # set starting stat values using AttributeHandler or db assignment
        char.attributes.add(stat.lower(), base)

# ---------------- Gender ----------------

def menunode_choose_gender(caller):
    text = "|wChoose Your Gender|n"
    options = [
        {"desc": "Male", "goto": (_set_gender, {"gender": "male"})},
        {"desc": "Female", "goto": (_set_gender, {"gender": "female"})},
        {"desc": "Back", "goto": "menunode_choose_class"},
    ]
    return text, options

def _set_gender(caller, raw_string, gender, **kwargs):
    caller.ndb.new_char.db.gender = gender
    return "menunode_stat_alloc"

# ---------------- Stat Allocation ----------------

def menunode_stat_alloc(caller):
    char = caller.ndb.new_char
    race_mods = next((r["stat_mods"] for r in races.RACE_LIST if r["name"] == char.db.race), {})
    class_mods = next((c["stat_mods"] for c in classes.CLASS_LIST if c["name"] == char.db.charclass), {})
    base_stats = {s: race_mods.get(s, 0) + class_mods.get(s, 0) for s in STAT_LIST}
    current = {s: char.db.get(s.lower(), 0) for s in STAT_LIST}
    spent = sum(max(current[s] - base_stats[s], 0) for s in STAT_LIST)
    remaining = STAT_POINTS - spent

    text = f"|wDistribute {STAT_POINTS} Points|n (Remaining: {remaining})\n"
    for s in STAT_LIST:
        text += f"{s}: {current[s]} (base: {base_stats[s]})\n"

    options = []
    if remaining > 0:
        for s in STAT_LIST:
            options.append({"desc": f"Add to {s}", "goto": (_adjust_stat, {"stat": s, "change": 1})})
    for s in STAT_LIST:
        if current[s] > base_stats[s]:
            options.append({"desc": f"Remove from {s}", "goto": (_adjust_stat, {"stat": s, "change": -1})})

    if remaining == 0:
        options.append({"desc": "Continue", "goto": "menunode_choose_name"})

    options.append({"desc": "Back", "goto": "menunode_choose_gender"})
    return text, options

def _adjust_stat(caller, raw_string, stat, change, **kwargs):
    char = caller.ndb.new_char
    current_val = char.db.get(stat.lower(), 0)
    race_mods = next((r["stat_mods"] for r in races.RACE_LIST if r["name"] == char.db.race), {})
    class_mods = next((c["stat_mods"] for c in classes.CLASS_LIST if c["name"] == char.db.charclass), {})
    base_val = race_mods.get(stat, 0) + class_mods.get(stat, 0)
    if current_val + change < base_val:
        return "menunode_stat_alloc"
    # update the stat via AttributeHandler or db assignment
    char.attributes.add(stat.lower(), current_val + change)
    return "menunode_stat_alloc"

# ---------------- Name ----------------

def menunode_choose_name(caller, raw_string="", **kwargs):
    error = kwargs.get("error", "")
    text = f"|wName Your Character|n\n{error}\nEnter your character's name:"
    options = {"key": "_default", "goto": _set_name}
    return text, options

def _set_name(caller, raw_string, **kwargs):
    name = raw_string.strip().capitalize()
    if not name or Character.objects.filter_family(db_key__iexact=name):
        return "menunode_choose_name", {"error": f"|r{name} is already taken or invalid.|n"}
    caller.ndb.new_char.key = name
    return "menunode_description"

# ---------------- Description ----------------

def menunode_description(caller, raw_string="", **kwargs):
    text = "|wDescribe Your Character|n\nHow do they look, act, or carry themselves?"
    options = {"key": "_default", "goto": _set_description}
    return text, options

def _set_description(caller, raw_string, **kwargs):
    caller.ndb.new_char.db.desc = raw_string.strip()
    return "menunode_confirm"

# ---------------- Confirm ----------------

def menunode_confirm(caller, **kwargs):
    char = caller.ndb.new_char
    text = f"|wFinal Confirmation|n\n"
    text += f"Race: {char.db.race}\nClass: {char.db.charclass}\nGender: {char.db.gender}\n"
    for s in STAT_LIST:
        text += f"{s}: {char.db.get(s.lower(), 0)}\n"
    text += f"Name: {char.key}\nDescription: {char.db.desc}\n\nIs everything correct?"

    options = [
        {"desc": "Yes, finish!", "goto": "menunode_finish"},
        {"desc": "No, start over", "goto": "menunode_welcome"},
    ]
    return text, options

def menunode_finish(caller, **kwargs):
    char = caller.ndb.new_char
    start_room = char.search("East half of a plaza", global_search=True, quiet=True)
    if start_room:
        char.home = start_room[0]
        char.db.prelogout_location = start_room[0]

    # ensure all trait keys exist
    apply_stats(char)

    for stat in STAT_LIST:
        value = char.db.get(stat.lower(), 0)
        trait = char.traits.get(stat)
        if trait:
            trait.base = value
        # remove the temporary value stored on the attribute handler
        char.attributes.remove(stat.lower())

    # assign the newly created character to this account
    char.account = caller
    caller.characters.add(char)
    char.save()

    caller.db._last_puppet = char
    caller.ndb.new_char = None
    caller.msg("|gCharacter Created! You can now use |wic <name>|g to enter the game.|n")
    return "|gYour character has been saved. Use |wic %s|n to enter the world." % char.key, None
