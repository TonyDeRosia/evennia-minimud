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
    alist current

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
        "key": "rdel",
        "category": "Building",
        "text": """Help for rdel

Delete a room by its VNUM and remove the saved prototype.

Usage:
    rdel <vnum>

Switches:
    None

Arguments:
    vnum - room VNUM to delete

Examples:
    rdel 200001

Notes:
    - Removes any exits to or from the room.
    - Deletes the prototype file if present.

Related:
    help delroom
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
    - Body part prototypes like HEAD_PART and ARMS_PART can be spawned for corpses or loot.

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
    - {level}, {experience} - your level and experience points
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

Status effects include temporary conditions like |wstunned|n or
|wdefending|n applied during combat. They modify your stats or actions
until their duration expires.

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
        "key": "rmake",
        "category": "Building",
        "text": """
Help for rmake

Create an unlinked room in a registered area.

Usage:
    rmake <area> <number>

Switches:
    --force

Arguments:
    None

Examples:
    rmake dungeon 1

Notes:
    - The number must fall within the area's range.
    - The room is spawned from a saved prototype.
    - The room is not automatically linked to any others.
    - Use --force to replace an existing room at that VNUM.

Related:
    help ansi
""",
    },
    {
        "key": "rreg",
        "category": "Building",
        "text": """
Help for rreg

Assign the current room or a specified room to an area and number.

Usage:
    rreg <area> <number>
    rreg <room> <area> <number>

Switches:
    None

Arguments:
    None

Examples:
    rreg test 2
    rreg #10 test 3

Notes:
    - The number must fall within the area's range and be unique.

Related:
    help ansi
    """,
    },
    {
        "key": "rregall",
        "category": "Building",
        "text": """Help for rregall

Scan all stored room prototypes and create any missing rooms.

Usage:
    rregall

Switches:
    None

Arguments:
    None

Examples:
    rregall

Notes:
    - Only prototypes with an 'area' value are considered.
    - Existing rooms are left untouched.

Related:
    help ansi
""",
    },
    {
        "key": "rlist",
        "category": "Building",
        "text": """"
Help for rlist

List rooms in an area showing VNUM and name.

Usage:
    rlist [<area>]

Switches:
    None

Arguments:
    None

Examples:
    rlist
    rlist town

Notes:
    - Without an argument the command uses your current area's name.
    - Room prototypes and area room lists are included; missing rooms
      are shown as (unbuilt).

Related:
    help ansi
""",
    },
    {
        "key": "redit",
        "category": "Building",
        "text": """Help for redit

Edit room prototypes in a menu.

Usage:
    redit <vnum> – edit a prototype or fallback to the live room
    redit create <vnum> – create a new prototype
    redit vnum <old> <new> – change prototype VNUM
    redit live <vnum> – force edit of an existing room object

Switches:
    None

Arguments:
    None

Examples:
    None

Notes:
    - Invalid numbers list the allowed range and next free slot.
    - Use @nextvnum R to obtain a free number.
    - redit create immediately spawns a usable room and registers it to the area.
    - redit here <vnum> assigns the current room to that VNUM and opens the editor.

Related:
    help vnums
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
    - Modifiers use the form |wStat+Value|n or |wStat-Value|n and are comma separated.
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
    - Modifiers use the form |wStat+Value|n or |wStat-Value|n and are comma separated.
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
    - Modifiers use the form |wStat+Value|n or |wStat-Value|n and are comma separated.
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
    - Modifiers use the form |wStat+Value|n or |wStat-Value|n and are comma separated.
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
    - Modifiers use the form |wStat+Value|n or |wStat-Value|n and are comma separated.
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
    - Modifiers use the form |wStat+Value|n or |wStat-Value|n and are comma separated.
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
    - Modifiers use the form |wStat+Value|n or |wStat-Value|n and are comma separated.
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
    - Modifiers use the form |wStat+Value|n or |wStat-Value|n and are comma separated.

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

Assign a bounty to a character. Amounts are in copper coins.

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
        "key": "peace",
        "category": "Admin",
        "text": """
Help for peace

Stop all fighting in the current room.

Usage:
    peace

Switches:
    None

Arguments:
    None

Examples:
    None

Notes:
    - Ends combat for everyone present.

Related:
        help ansi
""",
    },
    {
        "key": "@debug_combat",
        "category": "Admin",
        "text": """
Help for @debug_combat

Display combat debug information for a target.

Usage:
    @debug_combat <target>

Switches:
    None

Arguments:
    target - character or object to inspect

Examples:
    @debug_combat Bob

Notes:
    - Shows persistent and non-persistent combat flags for the target.

Related:
    help ansi
""",
    },
    {
        "key": "@spawnreload",
        "category": "Admin",
        "text": """Help for @spawnreload

Reload all spawn entries from room prototype files.

Usage:
    @spawnreload

Switches:
    None

Arguments:
    None

Examples:
    @spawnreload

Notes:
    - Room spawns are automatically registered when prototypes are saved. Use
      this command if spawns fail to appear or after manually editing files.
""",
    },
    {
        "key": "@forcerespawn",
        "category": "Admin",
        "text": """Help for @forcerespawn

Immediately run spawn checks for a room.

Usage:
    @forcerespawn <room_vnum>

Switches:
    None

Arguments:
    <room_vnum> - room VNUM to respawn

Examples:
    @forcerespawn 200001
""",
    },
    {
        "key": "@showspawns",
        "category": "Building",
        "text": """Help for @showspawns

List spawn entries for your current room or the given VNUM.

Usage:
    @showspawns [room_vnum]

Switches:
    None

Arguments:
    room_vnum - optional room VNUM

Examples:
    @showspawns
    @showspawns 200001

Notes:
    - Room prototypes use |wspawn_interval|n. MobRespawnManager stores this as
      |wrespawn_rate|n, which is what this command displays.
""",
    },
    {
        "key": "mob spawn setup",
        "aliases": ["mobspawns"],
        "category": "Building",
        "text": """Help for mob spawn setup

This describes how to make NPCs automatically appear in a room.

1. Create or edit a mob prototype using |wcnpc|n or |wmobbuilder|n.
2. Save the prototype with a VNUM.
3. Use |wredit <room_vnum>|n and choose |wEdit spawns|n to add the prototype,
   max count and spawn interval (stored at runtime as |wrespawn_rate|n).
4. Save the room prototype. Spawns are registered automatically, but you can
   use |w@spawnreload|n or |wasave changed|n to refresh them manually.
5. Check spawns with |w@showspawns <room_vnum>|n.
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

List defined areas including their vnum range, list of room vnums, number of rooms,
registered mob prototypes, builders, flags, current age and reset interval.

Usage:
    alist
    alist current

Switches:
    None

Arguments:
    current - show only the area you are currently in

Examples:
    alist current

Notes:
    - The Vnums column lists all room ids defined for the area.

Related:
    help ansi
""",
    },
    {
        "key": "aedit",
        "category": "Building",
        "text": """Help for aedit

Edit or create area metadata.

Usage:
    aedit create <name> <start> <end>
    aedit range <name> <start> <end>
    aedit builders <name> <list>
    aedit flags <name> <list>
    aedit interval <name> <ticks>
    aedit rename <old> <new>
    aedit add <area|vnum> <room_vnum>

Switches:
    None

Arguments:
    None

Examples:
    aedit create dungeon 1 99
    aedit range town 200 299
    aedit builders town Alice,Bob
    aedit flags dungeon dark,safe
    aedit interval dungeon 60
    aedit rename oldarea newarea
    aedit add dungeon 5

Notes:
    - Builders and flags are comma separated lists.
    - The interval value is given in ticks.
    - Adding by room VNUM updates the area's range if needed.

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
        "text": """Help for dig

Create and link a new room.

Usage:
    @dig <direction> <vnum>
    dig <direction> <vnum>

Switches:
    --noreverse - skip the reverse exit

Arguments:
    None

Examples:
    @dig east 200005

Notes:
    - The VNUM must belong to a registered area.

Related:
    help ansi
""",
    },
    {
        "key": "@link",
        "aliases": ["link"],
        "category": "Building",
        "text": """Help for @link

Link one room to another by VNUM.

Usage:
    @link <direction> <vnum>
    link <direction> <vnum>

Switches:
    --noreverse - skip the reverse exit

Arguments:
    None

Examples:
    @link north 3002

Notes:
    - The target room must already exist.

Related:
    help ansi
""",
    },
    {
        "key": "deldir",
        "category": "Building",
        "text": """
Help for deldir

Delete an exit from the current room.

Usage:
    deldir <direction>

Switches:
    None

Arguments:
    None

Examples:
    None

Notes:
    - Removes the exit in the given direction. If the adjoining room
    - links back here, that exit is removed as well.

Related:
    help ansi
""",
    },
    {
        "key": "delroom",
        "category": "Building",
        "text": """
Help for delroom

Delete a room by direction or by area and number.

Usage:
    delroom <direction>
    delroom <area> <number>

Switches:
    None

Arguments:
    None

Examples:
    delroom north
    delroom test 2

Notes:
    - Removes any exits to or from the deleted room.

Related:
    help ansi
""",
    },
    {
        "key": "@teleport",
        "aliases": ["tp"],
        "category": "Building",
        "text": """
Help for @teleport (tp)

Teleport directly to a room. Usage: @teleport <area>:<number> or <number>

Usage:
    @teleport <area>:<number>
    tp <area>:<number>
    @teleport <number>
    tp <number>

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

View your character sheet, including remaining practice sessions and training points. Usage: score

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

Place a bounty on another character.

Usage:
    bounty <target> <amount> <currency>

Switches:
    None

Arguments:
    <target> - character to put a bounty on
    <amount> - how many coins to spend
    <currency> - coin type (copper, silver, gold or platinum)

Examples:
    None

Notes:
    - If ``<currency>`` is omitted it defaults to copper.
    - Accepted currencies: copper, silver, gold and platinum.

Related:
    help ansi
""",
    },
    {
        "key": "bank",
        "category": "General",
        "text": """Help for bank

Handle your stored coins with a banker.

Usage:
    bank balance
    bank deposit <amount [coin]>
    bank withdraw <amount [coin]>
    bank transfer <amount [coin]> <target>

Switches:
    None

Arguments:
    <amount> - number of coins
    <coin> - copper, silver, gold or platinum
    <target> - player to receive a transfer

Examples:
    bank deposit 50 silver
    bank withdraw 10 gold
    bank transfer 20 gold Bob

Notes:
    - Use while in the same room as a banker NPC.
    - Deposits convert coins upward automatically.
    - Withdrawals use higher denominations if necessary.

Related:
    help npc roles
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
        "key": "corpse",
        "aliases": ["corpses"],
        "category": "General",
        "text": """Help for corpse

Dead characters leave corpses that hold any items they carried.

Usage:
    get all corpse
    loot

Switches:
    None

Arguments:
    None

Examples:
    loot
    get all corpse

Notes:
    - |wloot|n is a shortcut for |wget all corpse|n.
    - Corpses decay after a time.

Related:
    help inventory
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
        "aliases": ["att", "hit", "shoot", "kill", "k"],
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
        "key": "berserk",
        "category": "Combat",
        "text": """Help for berserk

Enter a furious rage to temporarily increase your Strength at the cost of some stamina.

Usage:
    berserk

Notes:
    - Grants a short Strength buff but reduces your armor slightly.
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
        "key": "recall",
        "category": "General",
        "text": """Help for recall

Teleport to your personal recall location.

Usage:
    recall

Notes:
    - Set a location first with |wsetrecall|n.
    - Rooms flagged with |wno_recall|n block recall.

Related:
    help ansi
""",
    },
    {
        "key": "setrecall",
        "category": "General",
        "text": """Help for setrecall

Set your recall location to this room.

Usage:
    setrecall

Notes:
    - Only works in rooms flagged |wsanctuary|n.

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
Stamina Regen, Lifesteal, Leech, Cooldown Reduction, Initiative, Haste, Stealth,
Detection, Threat, Crafting Bonus.
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
    - NPC roles include merchant, questgiver, guildmaster,
      guild_receptionist, banker, trainer and wanderer.
    - NPC types include merchant, banker, trainer, wanderer,
      combatant and others.
    - Selecting the combatant type allows you to choose a combat class
      like Warrior or Mage.
    - The builder prompts for key, description, weight category,
      creature type, level, experience reward, optional HP MP SP values,
      primary stats, modifiers or buffs, combat class, behavior, skills,
      spells, resistances and AI type.
    - Mob specific fields such as act flags, resistances, skills and spells can
      now be configured directly in this menu along with an optional Script
      typeclass to run when the mob spawns.
    - Humanoid body type grants the standard equipment slots automatically.
      Quadrupeds receive head, body, front_legs and hind_legs and lack weapon
      slots. Unique lets you add or remove any slots in the next step.
    - Prompts accept |wback|n to return to the previous step or |wskip|n to
      keep the current value.
    - The skills prompt lists suggested abilities for the chosen class.
    - When multiple values are allowed, use comma or space separated lists as
      shown in each example.
    - After reviewing the summary choose |wYes|n to confirm and create or
      update the NPC.
    - Selecting |wYes|n spawns the NPC in your current location. Choosing
      |wYes & Save Prototype|n spawns the NPC and saves the prototype for
      later use.
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
    - Starts at a summary screen where you can jump directly to
      any section to edit.

Related:
    help cnpc
""",
    },
    {
        "key": "npc roles",
        "aliases": ["roles"],
        "category": "Building",
        "text": """Help for npc roles

NPC roles grant extra behavior to an NPC. Available roles are:
    merchant - sells items to players
    banker - stores currency for players
    trainer - teaches skills
    guildmaster - manages a guild
    guild_receptionist - greets guild visitors
    questgiver - offers quests
    combat_trainer - spars to improve combat ability
    event_npc - starts special events

Multiple roles may be assigned to the same NPC.
Use |wadd <role>|n or |wremove <role>|n when prompted.

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
The mob builder offers the same AI step for prototypes saved with
`@mcreate` or `@mset`. For scripted AI, store a callable path on
``npc.db.ai_script`` such as ``scripts.example_ai.patrol_ai``. Only modules
within the ``scripts`` package can be used.
Custom behaviors can be added by registering a class with
``combat.ai.register_ai`` and setting ``npc.db.ai_type`` to the new key.

Related:
    help cnpc
""",
    },
    {
        "key": "npc act flags",
        "aliases": ["actflags", "actflag"],
        "category": "Building",
        "text": """Help for npc act flags

NPC act flags enable automatic behavior:
    sentinel - never moves on its own
    wander - randomly move through exits
    stay_area - do not wander outside the current area
    scavenger - pick up items in the room
    aggressive - attack the first player seen
    wimpy - flee when health is low
    assist - join allies already fighting
    call_for_help - ask allies with assist to join
    noloot - drop no loot when killed

Set flags in the mob builder or with |w@mset <proto> actflags|n.

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

List NPC prototypes assigned to an area. Prototypes saved with |wcnpc|n while
standing in a room belonging to that area are added automatically.

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
        "key": "mobbuilder",
        "category": "Building",
        "text": """Help for mobbuilder

The |wmobbuilder|n command is now just an alias for |wcnpc|n. All of the
functionality lives in that command, so use either |wcnpc|n or |wmobbuilder|n
interchangeably. See |whelp cnpc|n for a complete overview of the builder.
The menu now includes prompts for weight category, choosing HP/MP/SP values,
adding modifiers or buffs and uses |wskip|n to keep defaults.
""",
    },
    {
        "key": "@mcreate",
        "category": "Building",
        "text": """Help for @mcreate

Create a new NPC prototype. The prototype data is stored in
``world/prototypes/npcs.json`` and does not affect any existing NPCs
until you update them with |w@editnpc|n. If ``copy_key`` is supplied the
new prototype will start as a duplicate of that entry.

After creating a prototype use |w@mset|n to edit additional fields like
stats, actflags or spells. View all stored prototypes with
|w@mlist|n.

Usage:
    @mcreate <key> [copy_key]

Examples:
    @mcreate merchant_02
    @mcreate elite_guard basic_guard
""",
    },
    {
        "key": "@mset",
        "category": "Building",
        "text": """Help for @mset

Edit a field on an NPC prototype stored in
``world/prototypes/npcs.json``. Existing NPCs remain unchanged unless
you later apply the prototype with |w@editnpc|n.

Values containing spaces should be quoted. Some fields accept a comma
separated list which will replace the old values.

Usage:
    @mset <proto> <field> <value>

Examples:
    @mset merchant level 10
    @mset merchant actflags aggressive,stay_area
""",
    },
    {
        "key": "@mstat",
        "category": "Building",
        "text": """Help for @mstat

Display stats for an NPC or prototype. Prototype information is read
from ``world/prototypes/npcs.json`` and this command never changes an
NPC. Use |w@editnpc|n for modifications. The output lists common combat
attributes along with any flags, resistances and languages defined on
the target. Use ``/rom`` for a condensed ROM-style summary.

Usage:
    @mstat [/rom] <npc or proto>

Examples:
    @mstat bandit
    @mstat /rom Bob
""",
    },
    {
        "key": "@mlist",
        "category": "Building",
        "text": """Help for @mlist

List NPC prototypes or counts of spawned NPCs. Prototypes are read from
``world/prototypes/npcs.json``. Listing does not modify any NPCs; use
|w@editnpc|n if you need to update them.

You may filter results with ``class=<name>``, ``race=<name>``,
``role=<name>``, ``tag=<tag>`` or ``zone=<area>``. Use ``/room`` to count
NPCs present in your current room or ``/area`` for the entire area. The
table shows columns for VNUM, Key, Status, Level, Class, Primary Role,
Roles and Count. Finalized prototypes display ``yes`` in the Status
column.

Usage:
    @mlist [area] [/room|/area] [filters]

Examples:
    @mlist
    @mlist town
    @mlist /room
""",
    },
    {
        "key": "@mspawn",
        "category": "Building",
        "text": """Help for @mspawn

Spawn an NPC from a prototype defined in
``world/prototypes/npcs.json``. Spawning creates a new NPC and leaves
existing ones untouched. Modify live NPCs with |w@editnpc|n.

Prototypes made with |wmobbuilder|n are prefixed with ``mob_``. Use the
full key when spawning those NPCs.

Usage:
    @mspawn <prototype|M<number>>

Examples:
    @mspawn bandit
    @mspawn mob_guard
    @mspawn M200001

Notes:
    - ``M<number>`` spawns a prototype by its VNUM.
    - NPCs spawned this way are tagged ``M<number>`` for easy lookup
      with ``search_tag``.
    - Saving a prototype with a VNUM automatically registers it for
      ``@mspawn M<number>``.
""",
    },
    {
        "key": "@quickmob",
        "category": "Building",
        "text": """Help for @quickmob

Quickly create a mob from a template. The command reserves a VNUM and
opens the builder on the review screen so you can tweak the values before
spawning. Selecting |wYes & Save Prototype|n will also register the
prototype for ``@mspawn M<number>``.

Usage:
    @quickmob <key> [template]

Example:
    @quickmob goblin warrior

Notes:
    - Templates are defined in ``world.templates.mob_templates``.
    - The mob is spawned after you confirm the menu options.
""",
    },
    {
        "key": "@mobtemplate",
        "category": "Building",
        "text": """Help for @mobtemplate

Load a predefined mob template into the current build session. Run this
before ``cnpc``, ``@quickmob`` or ``medit create`` to start with preset
stats.

Usage:
    @mobtemplate list
    @mobtemplate <template>

Example:
    @mobtemplate warrior

Notes:
    - Templates are defined in ``world.templates.mob_templates``.
    - Available templates include all combat classes such as warrior, mystic, wizard, sorcerer, mage, battlemage, necromancer, spellbinder, priest, paladin, druid, shaman, rogue, ranger, warlock, bard and swashbuckler plus the merchant utility template.
""",
    },
    {
        "key": "medit",
        "category": "Building",
        "text": """Help for medit

Open the NPC builder for a numeric prototype. ``create`` reserves the
number, loads a basic template and starts the builder from the beginning.
After editing choose |wYes & Save Prototype|n to spawn the mob and save the
prototype.

Usage:
    medit <vnum>
    medit create <vnum>

Example:
    medit create 10

Notes:
    - Invalid numbers list the allowed range and next free slot.
    - The mob is spawned when you finish the menu.
""",
    },
    {
        "key": "@mobpreview",
        "category": "Building",
        "text": """Help for @mobpreview

Spawn a prototype temporarily in your room. The NPC
disappears automatically after a short delay.

Usage:
    @mobpreview <prototype>

Example:
    @mobpreview goblin
""",
    },
    {
        "key": "@mobvalidate",
        "category": "Building",
        "text": """Help for @mobvalidate

Check a stored prototype for common problems like zero HP or conflicting
act flags. Displays a list of warnings or confirms that no issues were
found.

Usage:
    @mobvalidate <prototype>

Example:
    @mobvalidate goblin
""",
    },
    {
        "key": "@mobexport",
        "category": "Building",
        "text": """Help for @mobexport

Write a stored prototype to a JSON file in the directory defined by ``PROTOTYPE_NPC_EXPORT_DIR``. The filename may omit the ``.json`` extension. Existing files will be overwritten.

Usage:
    @mobexport <proto> <file>

Example:
    @mobexport goblin goblin.json
""",
    },
    {
        "key": "@mobimport",
        "category": "Building",
        "text": """Help for @mobimport

Load prototype data from a JSON file previously exported with ``@mobexport``. The loaded prototype will be registered and replace any existing entry with the same key.

Usage:
    @mobimport <file>

Example:
    @mobimport goblin.json
""",
    },
    {
        "key": "@mobproto",
        "category": "Building",
        "text": """Help for @mobproto

Manage VNUM-based NPC prototypes. Creating or editing a prototype
registers it in the mob database so it appears in ``@mlist`` automatically.

Usage:
    @mobproto create <vnum> <name>
    @mobproto set <vnum> <field> <value>
    @mobproto list
    @mobproto spawn <vnum> [room]
    @mobproto edit <vnum>
    @mobproto delete <vnum>
    @mobproto diff <vnum1> <vnum2>

Examples:
    @mobproto create 1 goblin
    @mobproto set 1 level 5
    @mobproto spawn 1

Notes:
    - Deleting fails if live NPCs exist for the VNUM.
""",
    },
    {
        "key": "@makeshop",
        "category": "Building",
        "text": """Help for @makeshop

Add shop data to an NPC prototype. If the prototype already has a shop
no changes are made.

Usage:
    @makeshop <prototype>

Example:
    @makeshop merchant
""",
    },
    {
        "key": "@shopset",
        "category": "Building",
        "text": """Help for @shopset

Modify fields on a prototype's shop entry. Valid fields are buy, sell,
hours and types. Item types should be a comma separated list.

Usage:
    @shopset <proto> <buy|sell|hours|types> <value>

Examples:
    @shopset merchant buy 120
    @shopset merchant types weapon,armor
""",
    },
    {
        "key": "@shopstat",
        "category": "Building",
        "text": """Help for @shopstat

Show the shop configuration for a prototype.

Usage:
    @shopstat <prototype>

Example:
    @shopstat merchant
""",
    },
    {
        "key": "@makerepair",
        "category": "Building",
        "text": """Help for @makerepair

Create repair shop data on a prototype. Does nothing if repair info
already exists.

Usage:
    @makerepair <prototype>

Example:
    @makerepair smith
""",
    },
    {
        "key": "@repairset",
        "category": "Building",
        "text": """Help for @repairset

Edit fields on a prototype's repair data. Fields are cost, hours and
types. Types is a comma separated list of allowed item types.

Usage:
    @repairset <proto> <cost|hours|types> <value>

Examples:
    @repairset smith cost 150
    @repairset smith types weapon,armor
""",
    },
    {
        "key": "@repairstat",
        "category": "Building",
        "text": """Help for @repairstat

Display repair shop settings stored on a prototype.

Usage:
    @repairstat <prototype>

Example:
    @repairstat smith
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
    hour       - fires at a specific game hour
    hour_prog  - alias of hour
    time       - fires at an exact HH:MM time
    time_prog  - alias of time

Reactions:
    say <text>         - speak
    emote/pose <text>  - emote
    move <cmd>         - perform a movement command
    attack [target]    - attack a character
    script <module.fn> - call a Python function
    <command>          - run any other command string

Conditions:
    percent <pct>   - only run if a random roll succeeds
    combat <0|1>    - requires the NPC be in or out of combat
    bribe <amount>  - minimum coin value given
    hp_pct <pct>    - fires below this health percent

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

Example:
    {"on_attack": [{"hp_pct": 50, "response": "say I'm badly hurt!"}]}

Related:
    help cnpc
    help mptriggers
    help optriggers
    help rptriggers
    help mpcommands
    help ifchecks
""",
    },
    {
        "key": "mptriggers",
        "category": "Building",
        "text": """Help for mptriggers

Mob programs use MPTRIGGERS to react to events around an NPC.

Common examples:
    act_prog <text>      - something nearby contains <text>
    greet_prog           - a player enters the room
    random_prog <pct>    - fires randomly by percent
    fight_prog <pct>     - during combat rounds
    death_prog           - the mob dies
    bribe_prog <amt>     - given coins worth <amt>
    give_prog <item>     - given a matching item
    speech_prog <text>   - hears someone speak <text>

Programs are added on the prototype using #MOBPROGS.

Related:
    help mpcommands
    help ifchecks
""",
    },
    {
        "key": "optriggers",
        "category": "Building",
        "text": """Help for optriggers

OPTRIGGERS fire when objects are interacted with.

Common triggers:
    get_prog           - item is picked up
    drop_prog          - item is dropped
    wear_prog          - worn by a character
    remove_prog        - removed from a slot
    sac_prog           - sacrificed or destroyed
    timer_prog         - when a set timer expires
    speech_prog <txt>  - words spoken near the item

Related:
    help mpcommands
    help ifchecks
""",
    },
    {
        "key": "rptriggers",
        "category": "Building",
        "text": """Help for rptriggers

RPTRIGGERS belong to rooms and run when players or NPCs act there.

Examples:
    enter_prog         - someone enters
    leave_prog         - someone leaves
    sleep_prog         - someone sleeps here
    time_prog <hour>   - at a specific game hour
    hour_prog <hour>   - alias of time_prog
    rand_prog <pct>    - random chance
    speech_prog <txt>  - hears someone speak <txt>

Related:
    help mpcommands
    help ifchecks
""",
    },
    {
        "key": "mpcommands",
        "category": "Building",
        "text": """Help for mpcommands

MPCOMMANDS are used inside mob, object and room programs.

Some useful commands:
    mob echo <msg>          - message the room
    mob goto <room>        - move the mob
    mob oload <vnum>       - load an object
    mob mload <vnum>       - load another mob
    mob purge <target>     - delete target
    mob transfer <vict> <room> - move a character
    mob force <vict> <cmd> - force a command
    mob delay <ticks>      - wait before continuing

See also |whelp ifchecks|n for conditional logic.
""",
    },
    {
        "key": "ifchecks",
        "category": "Building",
        "text": """Help for ifchecks

IFCHECKS provide conditions for MPCOMMANDS.

Format:
    if <check>
        <commands>
    else
        <commands>
    endif

Common checks:
    rand(<pct>)       - random chance
    ispc($n)          - actor is a player
    carries($n,obj)   - actor carries object
    level($n) > num   - compare level
    roomvnum() == id  - check current room

Checks may examine $n (actor), $i (object) and other variables.
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
Some spells list a supporting skill such as |wspellcasting|n. Every 10 points in
that skill grants +1% casting success chance.
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
    {
        "key": "loot tables",
        "aliases": ["loottable", "loot"],
        "category": "Building",
        "text": """Help for loot tables

Loot tables control random item drops from NPCs. Each entry is a mapping with
the prototype key or object VNUM and drop chance::

    [{"proto": "RAW_MEAT", "chance": 50}]

Set ``loot_table`` on an NPC prototype with |w@mset|n using JSON syntax.

Usage:
    @mset <proto> loot_table <json>

Examples:
    @mset wolf loot_table "[{\"proto\": 100001, \"chance\": 75}]"
    @mset bandit loot_table "[{\"proto\": \"IRON_SWORD\", \"chance\": 25}]"
    @mset goblin loot_table "[{\"proto\": \"gold\", \"chance\": 100, \"amount\": \"1d4+1\"}]"

Notes:
    - ``chance`` is a percent from 1-100.
    - Items with 100% chance always drop.
    - ``guaranteed_after`` optionally guarantees the item will drop after the
      given number of failed attempts.
    - ``amount`` may be a number or dice string when dropping coins.

Related:
    help cnpc
""",
    },
    {
        "key": "damage types",
        "aliases": ["damage", "elemental damage"],
        "category": "Combat",
        "text": """Help for damage types

Attacks are categorized as slashing, piercing, bludgeoning and elemental
types like fire or shadow. NPCs may gain resistances during the builder.
When damage is applied the engine checks these resistances and multiplies
the amount accordingly. Values below 1.0 mean the target resists that
type while values above 1.0 indicate vulnerability.
""",
    },
    {
        "key": "combat system",
        "aliases": ["combat"],
        "category": "Combat",
        "text": """Help for combat system

Combat is round based. Use |wattack <target>|n to begin a fight then
queue actions like attacks or skills each round. Status effects such as
|wstunned|n come from abilities and expire after a few ticks. Check them
with |waffects|n or |wstatus|n.

NPC behavior is controlled by an AI type set in the |wcnpc|n builder or
|wmobbuilder|n. Available types are passive, aggressive, defensive,
wander and scripted. Scripted AI runs the callback stored on
|wnpc.db.ai_script|n.
Additional AI classes can be registered with ``combat.ai.register_ai``.
""",
    },
    {
        "key": "builder types cnpc",
        "category": "Building",
        "text": """Help for builder types cnpc

Launch a quick NPC creation prompt. Follow the questions and a new
NPC will appear in your location.

Usage:
    builder types cnpc <name>
""",
    },
    {
        "key": "vnums",
        "category": "Building",
        "text": """Help for vnums

VNUMs are numeric identifiers reserved in a registry. Each category has a
dedicated range:

    NPCs: 1-99999
    Objects: 100000-199999
    Rooms: 200000-299999

Use |w@nextvnum <I|M|R|O|Q|S>|n to fetch the next free number. Prefix the
value with its letter, like |wM5|n, when spawning or referencing by VNUM.
NPCs spawned from a VNUM automatically gain a |wM<number>|n tag so you can
find them later with |wsearch_tag(key="M<number>", category="vnum")|n.
Invalid VNUMs will include the allowed range and next free slot in the error message.
""",
    },
    {
        "key": "nextvnum",
        "category": "Building",
        "text": """Help for nextvnum

Fetch the next unused VNUM for a category.

Usage:
    @nextvnum <I|M|R|O|Q|S>

Switches:
    None

Arguments:
    None

Examples:
    @nextvnum M

Notes:
    - I and O return an object VNUM.
    - The number is reserved immediately.

Related:
    help ansi
""",
    },
    {
        "key": "listvnums",
        "category": "Building",
        "text": """Help for listvnums

Show a few unused VNUMs without reserving them.

Usage:
    @listvnums <npc|room|object> [area]

Switches:
    None

Arguments:
    category - vnum type to check (npc, room, object)
    area - optional area name to limit the search

Examples:
    @listvnums npc
    @listvnums room town

Notes:
    - Lists the next five free numbers.
    - Does not reserve the VNUMs.

Related:
    help vnums
""",
    },
]
