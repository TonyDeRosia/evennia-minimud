r"""
Evennia settings file.

Remember:

Don't copy more from the default file than you actually intend to
change; this will make sure that you don't overload upstream updates
unnecessarily.

When changing a setting requiring a file system path (like
path/to/actual/file.py), use GAME_DIR and EVENNIA_DIR to reference
your game folder and the Evennia library folders respectively. Python
paths (path.to.module) should be given relative to the game's root
folder (typeclasses.foo) whereas paths within the Evennia library
needs to be given explicitly (evennia.foo).

If you want to share your game dir, including its settings, you can
put secret game- or server-specific settings in secret_settings.py.

"""

# Use the defaults from Evennia unless explicitly overridden
from evennia.settings_default import *
from pathlib import Path

######################################################################
# Evennia base server config
######################################################################

# This is the name of your game. Make it catchy!
SERVERNAME = "MiniMUD the RPG"

# Defines the base character type as PlayerCharacter instead of Character
BASE_CHARACTER_TYPECLASS = "typeclasses.characters.PlayerCharacter"

# Enable command abbreviation matching
CMD_IGNORE_INVALID_ABBREVIATIONS = False

# Use the project MuxCommand so prompts refresh after every command
COMMAND_DEFAULT_CLASS = "commands.command.MuxCommand"

# Default experience reward given per NPC level when creating mobs
DEFAULT_XP_PER_LEVEL = 10

# Experience required to advance from ``level`` to ``level + 1``
XP_TO_LEVEL = lambda level: 100 + (level ** 2 * 20)

# Whether excess XP carries over when leveling
XP_CARRY_OVER = False

# Default area to assign rooms that lack one
DEFAULT_AREA_NAME = "Starter Zone"
DEFAULT_AREA_START = 200000
DEFAULT_AREA_END = 200999

# ----------------------------------------------------------------------
# Corpse decay settings
# ----------------------------------------------------------------------
# Minimum and maximum minutes before an NPC corpse decays. The exact
# duration is chosen randomly for each corpse within this range.
CORPSE_DECAY_MIN = 5
CORPSE_DECAY_MAX = 10

# When ``True`` a corpse will decay even if being carried in someone's
# inventory. Set to ``False`` to only allow decay when lying in a room.
ALLOW_CORPSE_DECAY_IN_INVENTORY = False

######################################################################
# Config for contrib packages
######################################################################

# XYZGrid - https://www.evennia.com/docs/latest/Contribs/Contrib-XYZGrid.html
EXTRA_LAUNCHER_COMMANDS["xyzgrid"] = "evennia.contrib.grid.xyzgrid.launchcmd.xyzcommand"
PROTOTYPE_MODULES += ["evennia.contrib.grid.xyzgrid.prototypes"]
# Custom prototype packages
PROTOTYPE_MODULES += [
    "world.prototypes.rooms",
    "world.prototypes.mobs",
    "world.prototypes.objects",
    "world.prototypes.areas",
]
XYZROOM_PROTOTYPE_OVERRIDE = {"typeclass": "typeclasses.rooms.XYGridRoom"}
# exits are stored as room.db.exits mappings

# File used for storing NPC prototypes
PROTOTYPE_NPC_FILE = Path(GAME_DIR) / "world" / "prototypes" / "npcs.json"

PROTOTYPE_NPC_EXPORT_DIR = Path(GAME_DIR) / "exports" / "npc_prototypes"

# File tracking used VNUMs
VNUM_REGISTRY_FILE = Path(GAME_DIR) / "world" / "vnum_registry.json"

# Log each combat tick when set to True
COMBAT_DEBUG_TICKS = False
# When True, include a damage summary at the end of each combat round
COMBAT_DEBUG_SUMMARY = False

# Clothing - https://www.evennia.com/docs/latest/Contribs/Contrib-Clothing.html#configuration
CLOTHING_WEARSTYLE_MAXLENGTH = 40
CLOTHING_TYPE_ORDERED = [
    "head",
    "jewelry",
    "chestguard",
    "top",
    "undershirt",
    "bracers",
    "gloves",
    "fullbody",
    "legguard",
    "bottom",
    "underpants",
    "socks",
    "shoes",
    "accessory",
]
CLOTHING_TYPE_AUTOCOVER = {
    "top": ["undershirt"],
    "chestguard": ["top", "undershirt"],
    "bottom": ["underpants"],
    "legguard": ["bottom", "underpants"],
    "fullbody": ["undershirt", "underpants"],
    "shoes": ["socks"],
}

CLOTHING_TYPE_LIMIT = {
    "chestguard": 1,
    "legguard": 1,
    "bracers": 1,
    "head": 1,
    "gloves": 1,
    "socks": 1,
    "shoes": 1,
}

# Crafting - https://www.evennia.com/docs/latest/Contribs/Contrib-Crafting.html
CRAFT_RECIPE_MODULES = [
    "world.recipes.smithing",
    "world.recipes.cooking",
]

# Character Creation - https://www.evennia.com/docs/latest/Contribs/Contrib-Character-Creator.html
CHARGEN_MENU = "world.chargen_menu"
AUTO_CREATE_CHARACTER_WITH_ACCOUNT = False
AUTO_PUPPET_ON_LOGIN = False
MAX_NR_CHARACTERS = 3

# EvMenu Login - https://www.evennia.com/docs/latest/Contribs/Contrib-Menu-Login.html
CMDSET_UNLOGGEDIN = "evennia.contrib.base_systems.menu_login.UnloggedinCmdSet"
CONNECTION_SCREEN_MODULE = "evennia.contrib.base_systems.menu_login.connection_screens"

######################################################################
# Settings given in secret_settings.py override those in this file.
######################################################################
try:
    from server.conf.secret_settings import *
except ImportError:
    from evennia.utils.logger import log_warn
    log_warn("secret_settings.py file not found or failed to import.")
