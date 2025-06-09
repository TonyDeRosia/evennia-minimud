"""
File-based help entries. These complements command-based help and help entries
added in the database using the `sethelp` command in-game.

Control where Evennia reads these entries with `settings.FILE_HELP_ENTRY_MODULES`,
which is a list of python-paths to modules to read.

A module like this should hold a global `HELP_ENTRY_DICTS` list, containing
dicts that each represent a help entry. If no `HELP_ENTRY_DICTS` variable is
given, all top-level variables that are dicts in the module are read as help
entries.

Each dict is on the form
::

    {'key': <str>,
     'text': <str>}``     # the actual help text. Can contain # subtopic sections
     'category': <str>,   # optional, otherwise settings.DEFAULT_HELP_CATEGORY
     'aliases': <list>,   # optional
     'locks': <str>       # optional, 'view' controls seeing in help index, 'read'
                          #           if the entry can be read. If 'view' is unset,
                          #           'read' is used for the index. If unset, everyone
                          #           can read/view the entry.

"""

HELP_ENTRY_DICTS = [
    {
        "key": "evennia",
        "aliases": ["ev"],
        "category": "General",
        "locks": "read:perm(Developer)",
        "text": """
Help for evennia

Evennia is a MU-game server and framework written in Python. You can read more
on https://www.evennia.com.

Usage:
    evennia

Switches:
    None

Arguments:
    None

Examples:
    None

Notes:
    - # subtopics
    - ## Installation
    - You'll find installation instructions on https://www.evennia.com.
    - ## Community
    - There are many ways to get help and communicate with other devs!
    - ### Discussions
    - The Discussions forum is found at
    https://github.com/evennia/evennia/discussions.
    - ### Discord
    - There is also a discord channel for chatting - connect using the
    - following link: https://discord.gg/AJJpcRUhtF

Related:
    help ansi
""",
    },
    {
        "key": "building",
        "category": "Building",
        "text": """
Help for building

Evennia comes with a bunch of default building commands. You can find a beginner
tutorial in the Evennia documentation.

Usage:
    building

Switches:
    None

Arguments:
    None

Examples:
    None

Notes:
    - Primary stats cap at 999.
    - Use @mcreate and @mset to manage NPC prototypes.
    - Shops and repairs use @makeshop/@shopset and @makerepair/@repairset.

Related:
    help ansi
""",
    },
    {
        "key": "prompt",
        "category": "General",
        "text": """
Help for prompt

Customize the information shown in your command prompt.

Usage:
    prompt

Switches:
    None

Arguments:
    None

Examples:
    |wprompt [HP:{hp}/{hpmax}] [SP:{sp}/{spmax}] {enc}>|n

Notes:
    - Use |wprompt|n to view your current prompt string.
    - Use |wprompt <format>|n to set a new one. The string may use the
    - following fields:
    - {hp}, {hpmax} - current and max health
    - {mp}, {mpmax} - current and max mana
    - {sp}, {spmax} - current and max stamina
    - {level}, {xp} - your level and experience points
    - {copper}, {silver}, {gold}, {platinum} - coins carried
    - {carry}, {capacity} - carry weight and capacity
    - {enc} - encumbrance level
    - Primary stats are capped at 999.

Related:
    help ansi
""",
    },
    {
        "key": "affects",
        "category": "General",
        "text": """
Help for affects

View your active buffs and status effects.

Usage:
    affects

Switches:
    None

Arguments:
    None

Examples:
    None

Notes:
    - Displays any active effects along with their remaining duration in ticks.

Related:
    help ansi
""",
    },
    {
        "key": "inspect",
        "category": "General",
        "text": """
Help for inspect

Examine an item for more information.

Usage:
    inspect <item>

Switches:
    None

Arguments:
    None

Examples:
    None

Notes:
    - Identified items reveal their weight, damage, slots,
    - buffs and any flags. Unidentified items only show a brief
    - description.

Related:
    help ansi
""",
    },
    {
        "key": "room flags",
        "aliases": ["rflags", "rflag"],
        "category": "Building",
        "text": """
Help for room flags

Rooms can be marked with special flags.

Usage:
    room flags

Switches:
    None

Arguments:
    None

Examples:
    None

Notes:
    - Use |wrflags|n to view flags on the current room.
    - Builders may add or remove them with |wrflag add <flag>|n
    - or |wrflag remove <flag>|n.
    - Use |wrflag list|n to show all valid flags.
    - Available flags:
    - dark - room is dark, requiring light to see.
    - nopvp - player versus player combat is blocked.
    - sanctuary - hostile actions are prevented.
    - indoors - counts as being indoors.
    - safe - NPCs won't start fights here.
    - no_recall - recall and teleport effects fail.
    - no_mount - mounts cannot be used.
    - no_flee - prevents fleeing from combat.
    - rest_area - resting recovers resources faster.

Related:
    help ansi
""",
    },
    {
        "key": "rrename",
        "aliases": ["roomrename", "renameroom", "rname"],
        "category": "Building",
        "text": """
Help for rrename

Rename the room you are currently in.

Usage:
    rrename <new name>

Switches:
    None

Arguments:
    None

Examples:
    None

Notes:
    - Changes the name of the current room.

Related:
    help ansi
""",
    },
    {
        "key": "rdesc",
        "aliases": ["roomdesc"],
        "category": "Building",
        "text": """
Help for rdesc

View or change the current room's description.

Usage:
    rdesc <new description>

Switches:
    None

Arguments:
    None

Examples:
    None

Notes:
    - With no description given, shows the current one.
    - ANSI color codes are supported.

Related:
    help ansi
""",
    },
    {
        "key": "rset",
        "category": "Building",
        "text": """
Help for rset

Set properties on the current room.

Usage:
    rset area <area name>
    rset id <number>

Switches:
    None

Arguments:
    None

Examples:
    None

Notes:
    - The id must be unique within the area's range.

Related:
    help ansi
""",
    },
    {
        "key": "ocreate",
        "category": "Building",
        "text": """
Help for ocreate

Create a generic object and put it in your inventory.

Usage:
    ocreate <name>

Switches:
    None

Arguments:
    None

Examples:
    None

Notes:
    - None

Related:
    help ansi
""",
    },
    {
        "key": "cweapon",
        "category": "Building",
        "text": """
Help for cweapon

Create a simple melee weapon.

Usage:
    cweapon [/unidentified] <name> <slot> <damage> <weight> [stat_mods] <description>

Switches:
    None

Arguments:
    None

Examples:
    cweapon "Flaming Sword" mainhand 2d6 3 STR+1, Attack Power+3 A blazing blade.

Notes:
    - A lowercase alias matching the final key is created automatically.
    - Valid slots are |wmainhand|n, |woffhand|n, |wmainhand/offhand|n or
    |wtwohanded|n.
    - Damage may be a flat number or an |wNdN|n dice string, which is stored on
    the item as given.
    - Optional stat modifiers can be provided as comma separated entries like
    |wSTR+2, Attack Power+5|n. Valid stats include all core and derived values.
    - Modifiers use the form |wStat+Value|n and are comma separated.
    - Enclose multiword or ANSI-colored names in quotes.
    - The item is a |ctypeclasses.gear.MeleeWeapon|n.
    - ANSI color codes are supported.
    - Add |w/unidentified|n before the name to create the item unidentified.

Related:
    help ansi
""",
    },
    {
        "key": "cshield",
        "category": "Building",
        "text": """
Help for cshield

Create a shield piece of armor.

Usage:
    cshield [/unidentified] <name> <armor> <block_rate> <weight> [modifiers] <description>

Switches:
    None

Arguments:
    None

Examples:
    cshield "Sturdy Kite" 2 8 3 STR+1, Critical Resist+4 A sturdy kite shield.

Notes:
    - The armor and block rate values are stored on the item.
    - Optional comma separated modifiers may be given, such as
    |wBlock Rate+3|n or |wSTR+2, Attack Power+5|n. Valid stats include
    all core and derived values.
    - Modifiers use the form |wStat+Value|n and are comma separated.
    - Enclose multiword or ANSI-colored names in quotes.
    - Add |w/unidentified|n before the name to create the shield unidentified.

Related:
    help ansi
""",
    },
    {
        "key": "carmor",
        "category": "Building",
        "text": """
Help for carmor

Create a wearable armor item.

Usage:
    carmor [/unidentified] <name> <slot> <weight> [stat_mods] <description>

Switches:
    None

Arguments:
    None

Examples:
    carmor "Ruby Helm" head 5 hp+5,armor+10,stamina_regen+2 A red magical helmet.

Notes:
    - Slot becomes the clothing type.
    - Add |w/unidentified|n before the name to create the armor unidentified.
    - Modifiers use the form |wStat+Value|n and are comma separated.
    - Enclose multiword or ANSI-colored names in quotes.

Related:
    help ansi
""",
    },
    {
        "key": "ctool",
        "category": "Building",
        "text": """
Help for ctool

Create a crafting tool.

Usage:
    ctool <name> [tag] [weight] [stat_mods] <description>

Switches:
    None

Arguments:
    None

Examples:
    ctool hammer smith 2 STR+2, Crafting Bonus+1 Heavy hammer.

Notes:
    - The tag is added with category 'crafting_tool'.
    - Modifiers use the form |wStat+Value|n and are comma separated.
    - Enclose multiword or ANSI-colored names in quotes.

Related:
    help ansi
""",
    },
    {
        "key": "cgear",
        "category": "Building",
        "text": """
Help for cgear

Generic helper for gear creation.

Usage:
    cgear [/unidentified] <typeclass> <name> [slot] [value] [weight] [stat_mods] <description>

Switches:
    None

Arguments:
    None

Examples:
    cgear typeclasses.objects.Object token accessory 1 1 STR+1, CON+2 A special token.

Notes:
    - Creates an object of the given typeclass and places it in your inventory.
    - Add |w/unidentified|n before the name to create the item unidentified.
    - Modifiers use the form |wStat+Value|n and are comma separated.
    - Enclose multiword or ANSI-colored names in quotes.

Related:
    help ansi
""",
    },
    {
        "key": "cring",
        "category": "Building",
        "text": """
Help for cring

Create a wearable ring.

Usage:
    cring [/unidentified] <name> [slot] [weight] [stat_mods] <description>

Switches:
    None

Arguments:
    None

Examples:
    cring "Ruby Ring" ring2 1 STR+1, Luck+2 A jeweled ring.

Notes:
    - Slot defaults to ring1. Use ring2 for the other finger.
    - Add |w/unidentified|n before the name to create the ring unidentified.
    - Modifiers use the form |wStat+Value|n and are comma separated.
    - Enclose multiword or ANSI-colored names in quotes.

Related:
    help ansi
""",
    },
    {
        "key": "ctrinket",
        "category": "Building",
        "text": """
Help for ctrinket

Create a wearable trinket or accessory.

Usage:
    ctrinket [/unidentified] <name> [weight] [stat_mods] <description>

Switches:
    None

Arguments:
    None

Examples:
    ctrinket "Lucky Charm" accessory 1 WIS+2, Stealth+3 A shimmering charm.

Notes:
    - Trinkets occupy the dedicated trinket slot.
    - Add |w/unidentified|n before the name to create the item unidentified.
    - Modifiers use the form |wStat+Value|n and are comma separated.
    - Enclose multiword or ANSI-colored names in quotes.

Related:
    help ansi
""",
    },
    {
        "key": "cfood",
        "category": "Building",
        "text": """
Help for cfood

Create an edible food item.

Usage:
    cfood <name> <sated_boost> <description>

Switches:
    None

Arguments:
    None

Examples:
    None

Notes:
    - Items are flagged edible automatically.
    - Weight is set to 1.

Related:
    help ansi
""",
    },
    {
        "key": "cdrink",
        "category": "Building",
        "text": """
Help for cdrink

Create a consumable drink.

Usage:
    cdrink <name> <sated_boost> <description>

Switches:
    None

Arguments:
    None

Examples:
    None

Notes:
    - Items are flagged edible automatically.
    - Weight is set to 1.

Related:
    help ansi
""",
    },
    {
        "key": "cpotion",
        "category": "Building",
        "text": """
Help for cpotion

Create a drinkable potion that modifies stats.

Usage:
    cpotion <name> <stat_mods> <description>

Switches:
    None

Arguments:
    None

Examples:
    None

Notes:
    - Items are flagged edible automatically.
    - Weight is set to 1.
    - Modifiers use the form |wStat+Value|n and are comma separated.

Related:
    help ansi
""",
    },
    {
        "key": "item flags",
        "aliases": ["setflag", "removeflag"],
        "category": "Building",
        "text": """
Help for item flags

Items may have special flags stored on them.

Usage:
    item flags

Switches:
    None

Arguments:
    None

Examples:
    None

Notes:
    - Flags are stored as tags in the |wflag|n category.
    - Use |wsetflag <item> <flag>|n to add a flag and
    - |wremoveflag <item> <flag>|n to remove it.
    - Common flags:
    - identified   - item is identified and can be used
    - equipment    - marks the object as equipable
    - stationary   - item cannot be moved
    - mainhand     - must be wielded in your main hand
    - offhand      - must be wielded in your off hand
    - shield       - occupies your shield slot
    - twohanded    - requires both hands free
    - unidentified - item is not yet identified
    - rare         - indicates special rarity

Related:
    help ansi
""",
    },
    {
        "key": "admin",
        "category": "Admin",
        "text": """
Help for admin

Commands reserved for administrators. These bypass normal limits and should be
used carefully. Most require `perm(Admin)` access.

Usage:
    admin

Switches:
    None

Arguments:
    None

Examples:
    None

Notes:
    - None

Related:
    help ansi
""",
    },
    {
        "key": "setstat",
        "aliases": ["set"],
        "category": "Admin",
        "text": """
Help for setstat

Change a character's stat directly.

Usage:
    setstat <target> <stat> <value>

Switches:
    None

Arguments:
    None

Examples:
    None

Notes:
    - Aliases:
    - set
    - The stat name accepts shorthands:
    - hp -> health
    - mp -> mana
    - sp -> stamina
    - This modifies the target's stat permanently. Creating or adjusting
    - stats incorrectly may break the character, so double-check your
    - inputs before committing changes.
    - Primary stats cannot exceed 999.

Related:
    help ansi
""",
    },
    {
        "key": "setattr",
        "category": "Admin",
        "text": """
Help for setattr

Set an arbitrary attribute on an object or character.

Usage:
    setattr <target> <attr> <value>

Switches:
    None

Arguments:
    None

Examples:
    None

Notes:
    - This will create the attribute if it does not already exist and
    - overwrite it if it does. Be certain you really want to change the
    - value as there is no undo command.

Related:
    help ansi
""",
    },
    {
        "key": "setbounty",
        "category": "Admin",
        "text": """
Help for setbounty

Assign a bounty to a character.

Usage:
    setbounty <target> <amount>

Switches:
    None

Arguments:
    None

Examples:
    None

Notes:
    - Adjusts the bounty value stored on the target. This has immediate
    - gameplay impact, so use it sparingly and verify the amount before
    - applying it.

Related:
    help ansi
""",
    },
    {
        "key": "slay",
        "category": "Admin",
        "text": """
Help for slay

Instantly reduce a target's health to zero.

Usage:
    slay <target>

Switches:
    None

Arguments:
    None

Examples:
    None

Notes:
    - This command will defeat the target regardless of protections or
    - current hit points. It should be reserved for emergencies or heavy
    - disciplinary action.

Related:
    help ansi
""",
    },
    {
        "key": "smite",
        "category": "Admin",
        "text": """
Help for smite

Reduce a target to a single hit point.

Usage:
    smite <target>

Switches:
    None

Arguments:
    None

Examples:
    None

Notes:
    - Smite leaves the target alive but on the brink of death. This is
    - useful for demonstrations or warnings when killing them would be too
    - extreme.

Related:
    help ansi
""",
    },
    {
        "key": "scan",
        "category": "Admin",
        "text": """
Help for scan

Look around and into adjacent rooms.

Usage:
    scan

Switches:
    None

Arguments:
    None

Examples:
    None

Notes:
    - Admins see additional information such as hidden objects, room flags
    - and the current HP/MP/SP of nearby characters. Use this power
    - responsibly and avoid revealing secret data to regular players.

Related:
    help ansi
""",
    },
    {
        "key": "restoreall",
        "category": "Admin",
        "text": """
Help for restoreall

Fully heal every player and remove all buffs and status effects.

Usage:
    restoreall

Switches:
    None

Arguments:
    None

Examples:
    None

Notes:
    - None

Related:
    help ansi
""",
    },
    {
        "key": "purge",
        "category": "Admin",
        "text": """
Help for purge

Delete unwanted objects.

Usage:
    purge
    purge <target>

Switches:
    None

Arguments:
    None

Examples:
    None

Notes:
    - Without arguments, removes everything in the current room
    - except for you. When given a target it deletes that object.
    - Players, rooms and exits are protected from being purged.

Related:
    help ansi
""",
    },
    {
        "key": "revive",
        "aliases": ["resurrect"],
        "category": "Combat",
        "text": """
Help for revive

Revive a defeated player at partial health.

Usage:
    revive <player>
    revive all

Switches:
    None

Arguments:
    None

Examples:
    None

Notes:
    - Using |wall|n revives every unconscious character in the game.

Related:
    help ansi
""",
    },
    {
        "key": "gcreate",
        "category": "Building",
        "text": """
Help for gcreate

Create a new guild.

Usage:
    gcreate <name>

Switches:
    None

Arguments:
    None

Examples:
    None

Notes:
    - None

Related:
    help ansi
""",
    },
    {
        "key": "grank",
        "category": "Building",
        "text": """
Help for grank

Manage guild rank titles.

Usage:
    grank add <guild> <level> <title>
    grank remove <guild> <level>
    grank list <guild>

Switches:
    None

Arguments:
    None

Examples:
    None

Notes:
    - None

Related:
    help ansi
""",
    },
    {
        "key": "gsethome",
        "category": "Building",
        "text": """
Help for gsethome

Set a guild's home location to your current room.

Usage:
    gsethome <guild>

Switches:
    None

Arguments:
    None

Examples:
    None

Notes:
    - None

Related:
    help ansi
""",
    },
    {
        "key": "gdesc",
        "category": "Building",
        "text": """
Help for gdesc

Set a guild's description.

Usage:
    gdesc <guild> <description>

Switches:
    None

Arguments:
    None

Examples:
    None

Notes:
    - None
    - ANSI color codes are supported.

Related:
    help ansi
""",
    },
    {
        "key": "gjoin",
        "category": "General",
        "text": """
Help for gjoin

Request to join a guild.

Usage:
    gjoin <guild>

Switches:
    None

Arguments:
    None

Examples:
    None

Notes:
    - None

Related:
    help ansi
""",
    },
    {
        "key": "gaccept",
        "category": "General",
        "text": """
Help for gaccept

Accept a player's guild request.

Usage:
    gaccept <player>

Switches:
    None

Arguments:
    None

Examples:
    None

Notes:
    - None

Related:
    help ansi
""",
    },
    {
        "key": "gpromote",
        "category": "General",
        "text": """
Help for gpromote

Increase a member's guild points.

Usage:
    gpromote <player> [amount]

Switches:
    None

Arguments:
    None

Examples:
    None

Notes:
    - None

Related:
    help ansi
""",
    },
    {
        "key": "gdemote",
        "category": "General",
        "text": """
Help for gdemote

Decrease a member's guild points.

Usage:
    gdemote <player> [amount]

Switches:
    None

Arguments:
    None

Examples:
    None

Notes:
    - None

Related:
    help ansi
""",
    },
    {
        "key": "gkick",
        "category": "General",
        "text": """
Help for gkick

Remove a member from your guild.

Usage:
    gkick <player>

Switches:
    None

Arguments:
    None

Examples:
    None

Notes:
    - None

Related:
    help ansi
""",
    },
    {
        "key": "gwho",
        "aliases": ["guildwho"],
        "category": "General",
        "text": """
Help for gwho

List members of your guild.

Usage:
    gwho

Switches:
    None

Arguments:
    None

Examples:
    None

Notes:
    - None

Related:
    help ansi
""",
    },
    {
        "key": "quest rewards",
        "category": "General",
        "text": """
Help for quest rewards

Some quests give coins of multiple types when completed.

Usage:
    quest rewards

Switches:
    None

Arguments:
    None

Examples:
    None

Notes:
    - Builders set the |wcurrency_reward|n field on the quest to a
    - mapping like ``{"platinum": 1, "gold": 5}``. Each coin type is
    - added to your wallet when you turn in the quest. Quests can also
    - award |wguild_points|n that count toward automatic promotion in a
    - guild.

Related:
    help ansi
""",
    },
    {
        "key": "alist",
        "category": "Building",
        "text": """
Help for alist

List all registered areas and their number ranges.

Usage:
    alist

Switches:
    None

Arguments:
    None

Examples:
    None

Notes:
    - None

Related:
    help ansi
""",
    },
    {
        "key": "amake",
        "category": "Building",
        "text": """
Help for amake

Register a new area. Usage: amake <name> <start>-<end>

Usage:
    amake

Switches:
    None

Arguments:
    None

Examples:
    None

Notes:
    - None

Related:
    help ansi
""",
    },
    {
        "key": "aset",
        "category": "Building",
        "text": """
Help for aset

Update an area's properties. Usage: aset <area> <name|range|desc> <value>

Usage:
    aset

Switches:
    None

Arguments:
    None

Examples:
    None

Notes:
    - None

Related:
    help ansi
""",
    },
    {
        "key": "rooms",
        "category": "Building",
        "text": """
Help for rooms

Show rooms belonging to your current area.

Usage:
    rooms

Switches:
    None

Arguments:
    None

Examples:
    None

Notes:
    - None

Related:
    help ansi
""",
    },
    {
        "key": "dig",
        "category": "Building",
        "text": """
Help for dig

Create a new room in a direction. Usage: dig <direction> [<area>:<number>]

Usage:
    dig <direction> [<area>:<number>]

Switches:
    None

Arguments:
    None

Examples:
    None

Notes:
    - None

Related:
    help ansi
""",
    },
    {
        "key": "@teleport",
        "category": "Building",
        "text": """
Help for @teleport

Teleport directly to a room. Usage: @teleport <area>:<number>

Usage:
    @teleport <area>:<number>

Switches:
    None

Arguments:
    None

Examples:
    None

Notes:
    - None

Related:
    help ansi
""",
    },
    {
        "key": "setdesc",
        "category": "Building",
        "text": """
Help for setdesc

Set an object's description. Usage: setdesc <target> <description>

Usage:
    setdesc <target> <description>

Switches:
    None

Arguments:
    None

Examples:
    None

Notes:
    - None
    - ANSI color codes are supported.

Related:
    help ansi
""",
    },
    {
        "key": "setweight",
        "category": "Building",
        "text": """
Help for setweight

Set an object's weight. Usage: setweight <target> <value>

Usage:
    setweight <target> <value>

Switches:
    None

Arguments:
    None

Examples:
    None

Notes:
    - None

Related:
    help ansi
""",
    },
    {
        "key": "setslot",
        "category": "Building",
        "text": """
Help for setslot

Define the slot or clothing type on an item. Usage: setslot <target> <slot>

Usage:
    setslot <target> <slot>

Switches:
    None

Arguments:
    None

Examples:
    None

Notes:
    - None

Related:
    help ansi
""",
    },
    {
        "key": "setdamage",
        "category": "Building",
        "text": """
Help for setdamage

Assign a damage value to a weapon. Usage: setdamage <target> <amount>

Usage:
    setdamage <target> <amount>

Switches:
    None

Arguments:
    None

Examples:
    None

Notes:
    - None

Related:
    help ansi
""",
    },
    {
        "key": "setbuff",
        "category": "Building",
        "text": """
Help for setbuff

Add a buff identifier to an object. Usage: setbuff <target> <buff>

Usage:
    setbuff <target> <buff>

Switches:
    None

Arguments:
    None

Examples:
    None

Notes:
    - None

Related:
    help ansi
""",
    },
    {
        "key": "qcreate",
        "category": "Building",
        "text": """
Help for qcreate

Create and register a new quest. Usage: qcreate <quest_key> "<title>"

Usage:
    qcreate <quest_key> "<title>"

Switches:
    None

Arguments:
    None

Examples:
    None

Notes:
    - Registers a new quest with the given key and title.

Related:
    help ansi
""",
    },
    {
        "key": "qset",
        "category": "Building",
        "text": """
Help for qset

Change quest attributes. Usage: qset <quest_key> <attr> <value>

Usage:
    qset <quest_key> <attribute> <value>

Switches:
    None

Arguments:
    None

Examples:
    None

Notes:
    - Updates attributes on an existing quest.

Related:
    help ansi
""",
    },
    {
        "key": "qitem",
        "category": "Building",
        "text": """
Help for qitem

Spawn a quest item. Usage: qitem <quest_key> <item_key>

Usage:
    qitem <quest_key> <item_key>

Switches:
    None

Arguments:
    None

Examples:
    None

Notes:
    - Creates and tags an item for the given quest.

Related:
    help ansi
""",
    },
    {
        "key": "qassign",
        "category": "Building",
        "text": """
Help for qassign

Assign a quest to an NPC. Usage: qassign <npc> <quest_key>

Usage:
    qassign <npc> <quest_key>

Switches:
    None

Arguments:
    None

Examples:
    None

Notes:
    - Adds the quest to an NPC so they can offer it.

Related:
    help ansi
""",
    },
    {
        "key": "qtag",
        "category": "Building",
        "text": """
Help for qtag

Set guild point rewards on a quest. Usage: qtag <quest_key> guild <guild>
<amount>

Usage:
    qtag <quest_key> guild <guild_name> <gp_value>

Switches:
    None

Arguments:
    None

Examples:
    None

Notes:
    - Sets guild point rewards for completing the quest.

Related:
    help ansi
""",
    },
    {
        "key": "score",
        "category": "General",
        "text": """
Help for score

View your character sheet. Usage: score

Usage:
    score

Switches:
    None

Arguments:
    None

Examples:
    None

Notes:
    - None

Related:
    help ansi
""",
    },
    {
        "key": "desc",
        "category": "General",
        "text": """
Help for desc

View or set your description. Usage: desc [text]

Usage:
    desc

Switches:
    None

Arguments:
    None

Examples:
    None

Notes:
    - None
    - ANSI color codes are supported.

Related:
    help ansi
""",
    },
    {
        "key": "finger",
        "category": "General",
        "text": """
Help for finger

Show information about a player. Usage: finger <player>

Usage:
    finger

Switches:
    None

Arguments:
    None

Examples:
    None

Notes:
    - None

Related:
    help ansi
""",
    },
    {
        "key": "bounty",
        "category": "General",
        "text": """
Help for bounty

Place a bounty on another character. Usage: bounty <target> <amount>

Usage:
    bounty

Switches:
    None

Arguments:
    None

Examples:
    None

Notes:
    - None

Related:
    help ansi
""",
    },
    {
        "key": "inventory",
        "category": "General",
        "text": """
Help for inventory

List items you are carrying. Usage: inventory [filter]

Usage:
    inventory

Switches:
    None

Arguments:
    None

Examples:
    None

Notes:
    - None

Related:
    help ansi
""",
    },
    {
        "key": "equipment",
        "category": "General",
        "text": """
Help for equipment

Show what you are wearing and wielding. Usage: equipment

Usage:
    equipment

Switches:
    None

Arguments:
    None

Examples:
    None

Notes:
    - None

Related:
    help ansi
""",
    },
    {
        "key": "buffs",
        "category": "General",
        "text": """
Help for buffs

Display active buff effects. Usage: buffs

Usage:
    buffs

Switches:
    None

Arguments:
    None

Examples:
    None

Notes:
    - None

Related:
    help ansi
""",
    },
    {
        "key": "title",
        "category": "General",
        "text": """
Help for title

View or change your title. Usage: title [new title]

Usage:
    title

Switches:
    None

Arguments:
    None

Examples:
    None

Notes:
    - None

Related:
    help ansi
""",
    },
    {
        "key": "questlist",
        "category": "General",
        "text": """
Help for questlist

List quests offered by NPCs here. Usage: questlist

Usage:
    questlist

Switches:
    None

Arguments:
    None

Examples:
    None

Notes:
    - None

Related:
    help ansi
""",
    },
    {
        "key": "accept",
        "category": "General",
        "text": """
Help for accept

Accept a quest. Usage: accept <quest>

Usage:
    accept

Switches:
    None

Arguments:
    None

Examples:
    None

Notes:
    - None

Related:
    help ansi
""",
    },
    {
        "key": "progress",
        "category": "General",
        "text": """
Help for progress

Show your progress on active quests. Usage: progress

Usage:
    progress

Switches:
    None

Arguments:
    None

Examples:
    None

Notes:
    - None

Related:
    help ansi
""",
    },
    {
        "key": "complete",
        "category": "General",
        "text": """
Help for complete

Turn in a completed quest. Usage: complete <quest>

Usage:
    complete

Switches:
    None

Arguments:
    None

Examples:
    None

Notes:
    - None

Related:
    help ansi
""",
    },
    {
        "key": "list",
        "category": "Here",
        "text": """
Help for list

View items a shop has for sale. Usage: list

Usage:
    list

Switches:
    None

Arguments:
    None

Examples:
    None

Notes:
    - None

Related:
    help ansi
""",
    },
    {
        "key": "buy",
        "category": "Here",
        "text": """
Help for buy

Purchase an item from a shop. Usage: buy <item>

Usage:
    buy

Switches:
    None

Arguments:
    None

Examples:
    None

Notes:
    - None

Related:
    help ansi
""",
    },
    {
        "key": "sell",
        "category": "Here",
        "text": """
Help for sell

Offer an item for sale to a shop. Usage: sell <item>

Usage:
    sell

Switches:
    None

Arguments:
    None

Examples:
    None

Notes:
    - None

Related:
    help ansi
""",
    },
    {
        "key": "guild",
        "category": "General",
        "text": """
Help for guild

Display information about your guild membership. Usage: guild

Usage:
    guild

Switches:
    None

Arguments:
    None

Examples:
    None

Notes:
    - None

Related:
    help ansi
""",
    },
    {
        "key": "gather",
        "category": "Here",
        "text": """
Help for gather

Collect resources from a gathering node. Usage: gather

Usage:
    gather

Switches:
    None

Arguments:
    None

Examples:
    None

Notes:
    - None

Related:
    help ansi
""",
    },
    {
        "key": "attack",
        "category": "Combat",
        "text": """
Help for attack

Attack an enemy. Usage: attack <target> [with <weapon>]

Usage:
    attack

Switches:
    None

Arguments:
    None

Examples:
    None

Notes:
    - None

Related:
    help ansi
""",
    },
    {
        "key": "wield",
        "category": "Combat",
        "text": """
Help for wield

Wield a weapon. Usage: wield <weapon> [in <hand>]

Usage:
    wield

Switches:
    None

Arguments:
    None

Examples:
    None

Notes:
    - None

Related:
    help ansi
""",
    },
    {
        "key": "unwield",
        "category": "Combat",
        "text": """
Help for unwield

Stop wielding a weapon. Usage: unwield <weapon>

Usage:
    unwield

Switches:
    None

Arguments:
    None

Examples:
    None

Notes:
    - None

Related:
    help ansi
""",
    },
    {
        "key": "flee",
        "category": "Combat",
        "text": """
Help for flee

Attempt to escape from combat. Usage: flee

Usage:
    flee

Switches:
    None

Arguments:
    None

Examples:
    None

Notes:
    - None

Related:
    help ansi
""",
    },
    {
        "key": "respawn",
        "category": "Combat",
        "text": """
Help for respawn

Return to town after being defeated. Usage: respawn

Usage:
    respawn

Switches:
    None

Arguments:
    None

Examples:
    None

Notes:
    - None

Related:
    help ansi
""",
    },
    {
        "key": "rest",
        "category": "General",
        "text": """
Help for rest

Sit down to recover stamina. Usage: rest

Usage:
    rest

Switches:
    None

Arguments:
    None

Examples:
    None

Notes:
    - None

Related:
    help ansi
""",
    },
    {
        "key": "sleep",
        "category": "General",
        "text": """
Help for sleep

Lie down and go to sleep. Usage: sleep

Usage:
    sleep

Switches:
    None

Arguments:
    None

Examples:
    None

Notes:
    - None

Related:
    help ansi
""",
    },
    {
        "key": "wake",
        "category": "General",
        "text": """
Help for wake

Stand up from rest or sleep. Usage: wake

Usage:
    wake

Switches:
    None

Arguments:
    None

Examples:
    None

Notes:
    - None

Related:
    help ansi
""",
    },
    {
        "key": "regeneration",
        "category": "General",
        "text": """
Help for regeneration

Health, mana and stamina are restored automatically. Each game tick you
recover amounts equal to your |whealth_regen|n, |wmana_regen|n and
|wstamina_regen|n stats. Passive 1-point-per-second healing has been removed.

Your current status modifies regeneration:
    - Standing: normal rates
    - Resting: 2x rates
    - Sleeping: 3x rates
Rooms flagged with |wrest_area|n grant an additional +1 multiplier on top of
your current status.

Usage:
    regeneration

Switches:
    None

Arguments:
    None

Examples:
    None

Notes:
    - None

Related:
    help ansi
""",
    },
    {
        "key": "statmods",
        "aliases": ["stat mods", "gear bonuses"],
        "category": "Building",
        "text": """
Help for statmods

These are the secondary stats that can be modified by gear creation commands.

Evasion, Armor, Magic Resist, Dodge, Block Rate, Parry Rate, Status Resist,
Critical Resist, Attack Power, Spell Power, Critical Chance, Critical Damage
Bonus, Accuracy, Armor Penetration, Spell Penetration, Health Regen, Mana Regen,
Stamina Regen, Lifesteal, Leech, Cooldown Reduction, Initiative, Stealth,
Detection, Threat, Movement Speed, Crafting Bonus, PvP Power, PvP Resilience,
Guild Honor Rank Modifiers.
""",
    },
    {
        "key": "cnpc",
        "aliases": ["npc", "createnpc"],
        "category": "Building",
        "text": """
Help for cnpc

Create or edit an NPC using a guided menu.

Usage:
    cnpc start <key>
    cnpc edit <npc>
    cnpc dev_spawn <proto>

Switches:
    None

Arguments:
    None

Examples:
    cnpc start merchant_01
    cnpc edit Bob
    cnpc dev_spawn basic_merchant

Notes:
    - Aliases:
    - npc
    - createnpc
    - NPC types include merchant, questgiver, guildmaster,
      guild_receptionist, banker, trainer and wanderer.
    - NPC classes include base, merchant, banker, trainer, wanderer,
      guildmaster, guild_receptionist, questgiver, combat_trainer and
      event_npc.
    - The builder prompts for description, NPC type, creature type, level,
      HP MP SP, primary stats, behavior, skills and AI type.
    - Humanoid body type grants the standard equipment slots automatically.
      Quadrupeds receive head, body, front_legs and hind_legs and lack weapon
      slots. Unique lets you add or remove any slots in the next step.
    - After reviewing the summary choose |wYes|n to confirm and create or
      update the NPC.
    - Use |wcnpc edit <npc>|n to modify an existing NPC.
    - At the triggers step you will see a menu to add, delete or list
      automatic reactions. Example:
          1) Add trigger
          2) Delete trigger
          3) List triggers
          4) Finish
      Choosing Add prompts for the event type, match text and reaction
      command.
    - |wcnpc dev_spawn|n quickly spawns prototype NPCs for testing (Developer only).
    - Example: |wcnpc dev_spawn basic_merchant|n
    - See |whelp triggers|n for available events and reactions.
    - ANSI color codes are supported in names and descriptions.

Related:
    help ansi
    help triggers
""",
    },
    {
        "key": "@editnpc",
        "category": "Building",
        "text": """Help for @editnpc

Open the NPC builder for an existing NPC.

Usage:
    @editnpc <npc>

Switches:
    None

Arguments:
    <npc> - the NPC to edit

Examples:
    @editnpc Bob

Notes:
    - Same as |wcnpc edit <npc>|n.

Related:
    help cnpc
""",
    },
    {
        "key": "npc roles",
        "aliases": ["roles"],
        "category": "Building",
        "text": """Help for npc roles

NPC roles grant extra behavior to an NPC. They are selected during the
`cnpc` builder at the roles step. Available roles are:
    merchant - sells items to players
    banker - stores currency for players
    trainer - teaches skills
    guildmaster - manages a guild
    guild_receptionist - greets guild visitors
    questgiver - offers quests
    combat_trainer - spars to improve combat ability
    event_npc - starts special events

Multiple roles may be assigned to the same NPC.

Related:
    help cnpc
""",
    },
    {
        "key": "npc ai",
        "aliases": ["ai"],
        "category": "Building",
        "text": """Help for npc ai

The `cnpc` builder lets you choose an AI type controlling basic behavior.
The available AI types are stored in `world.npc_handlers.ai`:
    passive - no automatic actions
    aggressive - attack the first player seen
    defensive - only fight when attacked
    wander - move through random exits
    scripted - run npc.db.ai_script callback

Set the type when prompted in the builder or edit the prototype data.
For scripted AI, store a callable path on ``npc.db.ai_script`` such as
``scripts.example_ai.patrol_ai``.

Related:
    help cnpc
""",
    },
    {
        "key": "@deletenpc",
        "category": "Building",
        "text": """Help for @deletenpc

Remove an NPC from the world.

Usage:
    @deletenpc <npc>

Switches:
    None

Arguments:
    <npc> - the NPC to delete

Examples:
    @deletenpc Bob

Notes:
    - Prompts for confirmation before deleting.

Related:
    help cnpc
""",
    },
    {
        "key": "@clonenpc",
        "category": "Building",
        "text": """Help for @clonenpc

Create a duplicate of an existing NPC.

Usage:
    @clonenpc <npc> [= <new_name>]

Switches:
    None

Arguments:
    <npc> - NPC to clone
    <new_name> - optional new key

Examples:
    @clonenpc Bob = Bob2

Notes:
    - The copy is placed in your current room.

Related:
    help cnpc
""",
    },
    {
        "key": "@spawnnpc",
        "category": "Building",
        "text": """Help for @spawnnpc

Spawn a saved NPC prototype.

Usage:
    @spawnnpc <prototype>
    @spawnnpc <area>/<prototype>

Switches:
    None

Arguments:
    <prototype> - key in world/prototypes/npcs.json

Examples:
    @spawnnpc basic_merchant
    @spawnnpc town/basic_merchant

Notes:
    - Prototypes are saved with the cnpc builder.

Related:
    help cnpc
""",
    },
    {
        "key": "@listnpcs",
        "category": "Building",
        "text": """Help for @listnpcs

List NPC prototypes assigned to an area.

Usage:
    @listnpcs <area>

Switches:
    None

Arguments:
    <area> - registered area name

Examples:
    @listnpcs town

Related:
    help cnpc
""",
    },
    {
        "key": "@dupnpc",
        "category": "Building",
        "text": """Help for @dupnpc

Duplicate an NPC prototype from an area's list.

Usage:
    @dupnpc <area>/<proto> [= <new_name>]

Switches:
    None

Arguments:
    <area> - area containing the prototype
    <proto> - prototype key to copy
    <new_name> - optional new key for the copy

Examples:
    @dupnpc town/basic_merchant = special_merchant

Related:
    help cnpc
""",
    },
    {
        "key": "triggers",
        "category": "Building",
        "text": """
Help for triggers

NPCs may react automatically to events. Triggers are grouped by event and
stored as lists of dictionaries with optional |wmatch|n text and one or more
|wresponse|n commands to run. Example::

    {"on_enter": [{"match": "", "response": "say Hello"}]}

Events:
    on_speak   - someone speaks in the room
    on_enter   - someone enters the room
    on_leave   - someone leaves the room
    on_give_item - the NPC receives an item
    on_look    - someone looks at the NPC
    on_attack  - combat starts or damage occurs
    on_timer   - once every game tick

Reactions:
    say <text>         - speak
    emote/pose <text>  - emote
    move <cmd>         - perform a movement command
    attack [target]    - attack a character
    script <module.fn> - call a Python function
    <command>          - run any other command string

The match text only applies to some events like |won_speak|n and |won_look|n.
Multiple triggers may be defined for the same event and each trigger can have
one or several responses.

Examples:
    Trigger Menu
        1) Add trigger
        2) Delete trigger
        3) List triggers
        4) Finish
    Adding a trigger asks for event type, optional match text and the
    command that should run when the event occurs.

Related:
    help cnpc
""",
    },
    {
        "key": "trainres",
        "category": "General",
        "text": """Help for trainres

Spend training points to permanently increase your health, mana or stamina.

Usage:
    trainres <hp|mp|sp> <amount>
""",
    },
    {
        "key": "spells",
        "category": "General",
        "text": """Help for spells

Learn new spells from trainers with |wlearn|n. Spells start at 25% proficiency.
Use practice sessions with |wlearn|n to raise proficiency up to 75%. Casting
spells will slowly increase proficiency to a maximum of 100%.
Usage: |wcast <spell> [on <target>]|n consumes mana based on the spell.
""",
    },
    {
        "key": "cast",
        "category": "General",
        "text": """Help for cast

Cast a spell that you have learned.

Usage:
    cast <spell> [on <target>]

Notes:
    - Each spell consumes mana when cast.
    - You must learn a spell before you can cast it.
""",
    },
    {
        "key": "learn",
        "aliases": ["trainspell"],
        "category": "General",
        "text": """Help for learn

Learn a spell from a trainer in your current location.
Each use costs one practice session and increases proficiency to 25% if the
spell was unknown or by 25% up to 75% if already learned.

Usage:
    learn
""",
    },
]
