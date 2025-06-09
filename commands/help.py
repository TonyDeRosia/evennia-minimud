from evennia.commands.default.help import CmdHelp as DefaultCmdHelp


class CmdHelp(DefaultCmdHelp):
    """Help command with alphabetically sorted index."""

    def format_help_index(
        self,
        cmd_help_dict=None,
        db_help_dict=None,
        title_lone_category=False,
        click_topics=True,
    ):
        """Ensure help topics are sorted alphabetically before display."""
        cmd_help_dict = {
            cat: sorted(topics)
            for cat, topics in sorted((cmd_help_dict or {}).items())
        }
        db_help_dict = {
            cat: sorted(topics)
            for cat, topics in sorted((db_help_dict or {}).items())
        }
        return super().format_help_index(
            cmd_help_dict, db_help_dict, title_lone_category, click_topics
        )

