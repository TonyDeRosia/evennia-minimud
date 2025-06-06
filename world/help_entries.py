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
        "category": "Building",
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
        "category": "Building",
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
        "category": "Building",
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
        "category": "Building",
        "text": """
            View or change the current room's description.

            Usage:
                rdesc <new description>

            With no description given, shows the current one.
        """,
    },
    {
        "key": "rset",
        "category": "Building",
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
        "category": "Building",
        "text": """
            Create a generic object and put it in your inventory.

            Usage:
                ocreate <name>
        """,
    },
    {
        "key": "cweapon",
        "category": "Building",
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
        "category": "Building",
        "text": """
            Create a shield piece of armor.

            Usage:
                cshield <name> [slot] [armor]

            The armor value is stored on the item.
        """,
    },
    {
        "key": "carmor",
        "category": "Building",
        "text": """
            Create a wearable armor item.

            Usage:
                carmor <name> [slot] [armor]

            Slot becomes the clothing type.
        """,
    },
    {
        "key": "ctool",
        "category": "Building",
        "text": """
            Create a crafting tool.

            Usage:
                ctool <name> [tag]

            The tag is added with category 'crafting_tool'.
        """,
    },
    {
        "key": "cgear",
        "category": "Building",
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
        "category": "Building",
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
        "category": "Admin",
        "text": """
            Commands reserved for administrators. These bypass normal limits and
            should be used carefully. Most require `perm(Admin)` access.
        """,
    },
    {
        "key": "setstat",
        "aliases": ["set"],
        "category": "Admin",
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
        "category": "Admin",
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
        "category": "Admin",
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
        "category": "Admin",
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
        "category": "Admin",
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
        "category": "Admin",
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
        "category": "Admin",
        "text": """
            Fully heal every player and remove all buffs and status effects.

            Usage:
                restoreall
        """,
    },
    {
        "key": "purge",
        "category": "Admin",
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
        "category": "Combat",
        "text": """
            Revive a defeated player at partial health.

            Usage:
                revive <player>
                revive all

            Using |wall|n revives every unconscious character in the game.
        """,
    },
    {
        "key": "gcreate",
        "category": "Building",
        "text": """
            Create a new guild.

            Usage:
                gcreate <name>
        """,
    },
    {
        "key": "grank",
        "category": "Building",
        "text": """
            Manage guild rank titles.

            Usage:
                grank add <guild> <level> <title>
                grank remove <guild> <level>
                grank list <guild>
        """,
    },
    {
        "key": "gsethome",
        "category": "Building",
        "text": """
            Set a guild's home location to your current room.

            Usage:
                gsethome <guild>
        """,
    },
    {
        "key": "gdesc",
        "category": "Building",
        "text": """
            Set a guild's description.

            Usage:
                gdesc <guild> <description>
        """,
    },
    {
        "key": "gjoin",
        "category": "General",
        "text": """
            Request to join a guild.

            Usage:
                gjoin <guild>
        """,
    },
    {
        "key": "gaccept",
        "category": "General",
        "text": """
            Accept a player's guild request.

            Usage:
                gaccept <player>
        """,
    },
    {
        "key": "gpromote",
        "category": "General",
        "text": """
            Increase a member's guild points.

            Usage:
                gpromote <player> [amount]
        """,
    },
    {
        "key": "gdemote",
        "category": "General",
        "text": """
            Decrease a member's guild points.

            Usage:
                gdemote <player> [amount]
        """,
    },
    {
        "key": "gkick",
        "category": "General",
        "text": """
            Remove a member from your guild.

            Usage:
                gkick <player>
        """,
    },
    {
        "key": "gwho",
        "aliases": ["guildwho"],
        "category": "General",
        "text": """
            List members of your guild.

            Usage:
                gwho
        """,
    },
    {
        "key": "quest rewards",
        "category": "General",
        "text": """
            Some quests give coins of multiple types when completed.

            Builders set the |wcurrency_reward|n field on the quest to a
            mapping like ``{"platinum": 1, "gold": 5}``. Each coin type is
            added to your wallet when you turn in the quest. Quests can also
            award |wguild_points|n that count toward automatic promotion in a
            guild.
        """,
    },
    {
        "key": "alist",
        "category": "Building",
        "text": """
            List all registered areas and their number ranges.
        """,
    },
    {
        "key": "amake",
        "category": "Building",
        "text": """
            Register a new area. Usage: amake <name> <start>-<end>
        """,
    },
    {
        "key": "aset",
        "category": "Building",
        "text": """
            Update an area's properties. Usage: aset <area> <name|range|desc> <value>
        """,
    },
    {
        "key": "rooms",
        "category": "Building",
        "text": """
            Show rooms belonging to your current area.
        """,
    },
    {
        "key": "dig",
        "category": "Building",
        "text": """
            Create a new room in a direction. Usage: dig <direction> [<area>:<number>]
        """,
    },
    {
        "key": "@teleport",
        "category": "Building",
        "text": """
            Teleport directly to a room. Usage: @teleport <area>:<number>
        """,
    },
    {
        "key": "setdesc",
        "category": "Building",
        "text": """
            Set an object's description. Usage: setdesc <target> <description>
        """,
    },
    {
        "key": "setweight",
        "category": "Building",
        "text": """
            Set an object's weight. Usage: setweight <target> <value>
        """,
    },
    {
        "key": "setslot",
        "category": "Building",
        "text": """
            Define the slot or clothing type on an item. Usage: setslot <target> <slot>
        """,
    },
    {
        "key": "setdamage",
        "category": "Building",
        "text": """
            Assign a damage value to a weapon. Usage: setdamage <target> <amount>
        """,
    },
    {
        "key": "setbuff",
        "category": "Building",
        "text": """
            Add a buff identifier to an object. Usage: setbuff <target> <buff>
        """,
    },
    {
        "key": "qcreate",
        "category": "Building",
        "text": """
            Create and register a new quest. Usage: qcreate <quest_key> "<title>"
        """,
    },
    {
        "key": "qset",
        "category": "Building",
        "text": """
            Change quest attributes. Usage: qset <quest_key> <attr> <value>
        """,
    },
    {
        "key": "qitem",
        "category": "Building",
        "text": """
            Spawn a quest item. Usage: qitem <quest_key> <item_key>
        """,
    },
    {
        "key": "qassign",
        "category": "Building",
        "text": """
            Assign a quest to an NPC. Usage: qassign <npc> <quest_key>
        """,
    },
    {
        "key": "qtag",
        "category": "Building",
        "text": """
            Set guild point rewards on a quest. Usage: qtag <quest_key> guild <guild> <amount>
        """,
    },
    {
        "key": "score",
        "category": "General",
        "text": """
            View your character sheet. Usage: score
        """,
    },
    {
        "key": "desc",
        "category": "General",
        "text": """
            View or set your description. Usage: desc [text]
        """,
    },
    {
        "key": "finger",
        "category": "General",
        "text": """
            Show information about a player. Usage: finger <player>
        """,
    },
    {
        "key": "bounty",
        "category": "General",
        "text": """
            Place a bounty on another character. Usage: bounty <target> <amount>
        """,
    },
    {
        "key": "inventory",
        "category": "General",
        "text": """
            List items you are carrying. Usage: inventory [filter]
        """,
    },
    {
        "key": "equipment",
        "category": "General",
        "text": """
            Show what you are wearing and wielding. Usage: equipment
        """,
    },
    {
        "key": "buffs",
        "category": "General",
        "text": """
            Display active buff effects. Usage: buffs
        """,
    },
    {
        "key": "title",
        "category": "General",
        "text": """
            View or change your title. Usage: title [new title]
        """,
    },
    {
        "key": "questlist",
        "category": "General",
        "text": """
            List quests offered by NPCs here. Usage: questlist
        """,
    },
    {
        "key": "accept",
        "category": "General",
        "text": """
            Accept a quest. Usage: accept <quest>
        """,
    },
    {
        "key": "progress",
        "category": "General",
        "text": """
            Show your progress on active quests. Usage: progress
        """,
    },
    {
        "key": "complete",
        "category": "General",
        "text": """
            Turn in a completed quest. Usage: complete <quest>
        """,
    },
    {
        "key": "list",
        "category": "Here",
        "text": """
            View items a shop has for sale. Usage: list
        """,
    },
    {
        "key": "buy",
        "category": "Here",
        "text": """
            Purchase an item from a shop. Usage: buy <item>
        """,
    },
    {
        "key": "sell",
        "category": "Here",
        "text": """
            Offer an item for sale to a shop. Usage: sell <item>
        """,
    },
    {
        "key": "guild",
        "category": "General",
        "text": """
            Display information about your guild membership. Usage: guild
        """,
    },
    {
        "key": "gather",
        "category": "Here",
        "text": """
            Collect resources from a gathering node. Usage: gather
        """,
    },
    {
        "key": "attack",
        "category": "Combat",
        "text": """
            Attack an enemy. Usage: attack <target> [with <weapon>]
        """,
    },
    {
        "key": "wield",
        "category": "Combat",
        "text": """
            Wield a weapon. Usage: wield <weapon> [in <hand>]
        """,
    },
    {
        "key": "unwield",
        "category": "Combat",
        "text": """
            Stop wielding a weapon. Usage: unwield <weapon>
        """,
    },
    {
        "key": "flee",
        "category": "Combat",
        "text": """
            Attempt to escape from combat. Usage: flee
        """,
    },
    {
        "key": "respawn",
        "category": "Combat",
        "text": """
            Return to town after being defeated. Usage: respawn
        """,
    },
    {
        "key": "rest",
        "category": "General",
        "text": """
            Sit down to recover stamina. Usage: rest
        """,
    },
    {
        "key": "sleep",
        "category": "General",
        "text": """
            Lie down and go to sleep. Usage: sleep
        """,
    },
    {
        "key": "wake",
        "category": "General",
        "text": """
            Stand up from rest or sleep. Usage: wake
        """,
    },
]
