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
            Evennia is a MU-game server and framework written in Python. You can read more
            on https://www.evennia.com.

            # subtopics

            ## Installation

            You'll find installation instructions on https://www.evennia.com.

            ## Community

            There are many ways to get help and communicate with other devs!

            ### Discussions

            The Discussions forum is found at https://github.com/evennia/evennia/discussions.

            ### Discord

            There is also a discord channel for chatting - connect using the
            following link: https://discord.gg/AJJpcRUhtF

        """,
    },
    {
        "key": "building",
        "category": "building",
        "text": """
            Evennia comes with a bunch of default building commands. You can
            find a beginner tutorial in the Evennia documentation.

        """,
    },
    {
        "key": "prompt",
        "category": "General",
        "text": """
            Customize the information shown in your command prompt.

            Use |wprompt|n to view your current prompt string.
            Use |wprompt <format>|n to set a new one. The string may use the
            following fields:

            {hp}, {hpmax} - current and max health
            {mp}, {mpmax} - current and max mana
            {sp}, {spmax} - current and max stamina
            {level}, {xp} - your level and experience points
            {copper}, {silver}, {gold}, {platinum} - coins carried
            {carry}, {capacity} - carry weight and capacity
            {enc} - encumbrance level

            Example:
                |wprompt [HP:{hp}/{hpmax}] [SP:{sp}/{spmax}] {enc}>|n
        """,
    },
    {
        "key": "affects",
        "category": "General",
        "text": """
            View your active buffs and status effects.

            Usage:
                affects

            Displays any active effects along with their remaining duration in ticks.
        """,
    },
    {
        "key": "inspect",
        "category": "General",
        "text": """
            Examine an item for more information.

            Usage:
                inspect <item>

            Identified items reveal their weight, damage, slots,
            buffs and any flags. Unidentified items only show a brief
            description.
        """,
    },
    {
        "key": "room flags",
        "aliases": ["rflags", "rflag"],
        "category": "building",
        "text": """
            Rooms can be marked with special flags.

            Use |wrflags|n to view flags on the current room.
            Builders may add or remove them with |wrflag add <flag>|n
            or |wrflag remove <flag>|n. Available flags:

            dark - room is dark, requiring light to see.
            nopvp - player versus player combat is blocked.
            sanctuary - hostile actions are prevented.
            indoors - counts as being indoors.
            safe - NPCs won't start fights here.
            no_recall - recall and teleport effects fail.
            no_mount - mounts cannot be used.
            no_flee - prevents fleeing from combat.
            rest_area - resting recovers resources faster.
        """,
    },
    {
        "key": "rrename",
        "aliases": ["roomrename", "renameroom", "rname"],
        "category": "building",
        "text": """
            Rename the room you are currently in.

            Usage:
                rrename <new name>

            Changes the name of the current room.
        """,
    },
    {
        "key": "rdesc",
        "aliases": ["roomdesc"],
        "category": "building",
        "text": """
            View or change the current room's description.

            Usage:
                rdesc <new description>

            With no description given, shows the current one.
        """,
    },
    {
        "key": "rset",
        "category": "building",
        "text": """
            Set properties on the current room.

            Usage:
                rset area <area name>
                rset id <number>

            The id must be unique within the area's range.
        """,
    },
    {
        "key": "ocreate",
        "category": "building",
        "text": """
            Create a generic object and put it in your inventory.

            Usage:
                ocreate <name>
        """,
    },
    {
        "key": "cweapon",
        "category": "building",
        "text": """
            Create a simple melee weapon.

            Usage:
                cweapon <name> <slot> <damage> [description]

            A lowercase alias matching the final key is created automatically.
            Valid slots are |wmainhand|n, |woffhand|n, |wmainhand/offhand|n or |wtwohanded|n.
            Damage may be a flat number or an |wNdN|n dice string, which is stored on the item as given.

            The item is a |ctypeclasses.gear.MeleeWeapon|n.
        """,
    },
    {
        "key": "cshield",
        "category": "building",
        "text": """
            Create a shield piece of armor.

            Usage:
                cshield <name> [slot] [armor]

            The armor value is stored on the item.
        """,
    },
    {
        "key": "carmor",
        "category": "building",
        "text": """
            Create a wearable armor item.

            Usage:
                carmor <name> [slot] [armor]

            Slot becomes the clothing type.
        """,
    },
    {
        "key": "ctool",
        "category": "building",
        "text": """
            Create a crafting tool.

            Usage:
                ctool <name> [tag]

            The tag is added with category 'crafting_tool'.
        """,
    },
    {
        "key": "cgear",
        "category": "building",
        "text": """
            Generic helper for gear creation.

            Usage:
                cgear <typeclass> <name> [slot] [value]

            Creates an object of the given typeclass and places it in your inventory.
        """,
    },
    {
        "key": "item flags",
        "aliases": ["setflag", "removeflag"],
        "category": "building",
        "text": """
            Items may have special flags stored on them.

            Use |wsetflag <item> <flag>|n to add a flag and
            |wremoveflag <item> <flag>|n to remove it.

            Some example flags:
                identified - item can be equipped or wielded
                equipment  - marks the object as equipable
                stationary - item cannot be moved
                mainhand   - must be wielded in your main hand
        """,
    },
    {
        "key": "admin",
        "category": "admin",
        "text": """
            Commands reserved for administrators. These bypass normal limits and
            should be used carefully. Most require `perm(Admin)` access.
        """,
    },
    {
        "key": "setstat",
        "aliases": ["set"],
        "category": "admin",
        "text": """
            Change a character's stat directly.

            Usage:
                setstat <target> <stat> <value>

            Aliases:
                set

            The stat name accepts shorthands:
                hp -> health
                mp -> mana
                sp -> stamina

            This modifies the target's stat permanently. Creating or adjusting
            stats incorrectly may break the character, so double-check your
            inputs before committing changes.
        """,
    },
    {
        "key": "setattr",
        "category": "admin",
        "text": """
            Set an arbitrary attribute on an object or character.

            Usage:
                setattr <target> <attr> <value>

            This will create the attribute if it does not already exist and
            overwrite it if it does. Be certain you really want to change the
            value as there is no undo command.
        """,
    },
    {
        "key": "setbounty",
        "category": "admin",
        "text": """
            Assign a bounty to a character.

            Usage:
                setbounty <target> <amount>

            Adjusts the bounty value stored on the target. This has immediate
            gameplay impact, so use it sparingly and verify the amount before
            applying it.
        """,
    },
    {
        "key": "slay",
        "category": "admin",
        "text": """
            Instantly reduce a target's health to zero.

            Usage:
                slay <target>

            This command will defeat the target regardless of protections or
            current hit points. It should be reserved for emergencies or heavy
            disciplinary action.
        """,
    },
    {
        "key": "smite",
        "category": "admin",
        "text": """
            Reduce a target to a single hit point.

            Usage:
                smite <target>

            Smite leaves the target alive but on the brink of death. This is
            useful for demonstrations or warnings when killing them would be too
            extreme.
        """,
    },
    {
        "key": "scan",
        "category": "admin",
        "text": """
            Look around and into adjacent rooms.

            Usage:
                scan

            Admins see additional information such as hidden objects, room flags
            and the current HP/MP/SP of nearby characters. Use this power
            responsibly and avoid revealing secret data to regular players.
        """,
    },
    {
        "key": "restoreall",
        "category": "admin",
        "text": """
            Fully heal every player and remove all buffs and status effects.

            Usage:
                restoreall
        """,
    },
    {
        "key": "purge",
        "category": "admin",
        "text": """
            Delete unwanted objects.

            Usage:
                purge
                purge <target>

            Without arguments, removes everything in the current room
            except for you. When given a target it deletes that object.
            Players, rooms and exits are protected from being purged.
        """,
    },
    {
        "key": "revive",
        "aliases": ["resurrect"],
        "category": "combat",
        "text": """
            Revive a defeated player at partial health.

            Usage:
                revive <player>
                revive all

            Using |wall|n revives every unconscious character in the game.
        """,
    },
]
