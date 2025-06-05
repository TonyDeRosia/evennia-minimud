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
]
