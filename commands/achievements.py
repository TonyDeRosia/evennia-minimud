from evennia import CmdSet
from .command import Command
from world.achievements import (
    AchievementManager,
    normalize_achievement_key,
)


class CmdAchievements(Command):
    """View your earned achievements.

    Usage:
        achievements

    Example:
        achievements
    """

    key = "achievements"
    aliases = ("achvs", "achv")
    help_category = "General"

    def func(self):
        caller = self.caller
        earned = caller.db.achievements or []
        if not earned:
            self.msg("You have not earned any achievements.")
            return
        lines = []
        for ach_key in earned:
            _, ach = AchievementManager.find(ach_key)
            if ach:
                title = ach.title or ach_key
                lines.append(f"{title} (+{ach.points})")
        if lines:
            self.msg("\n".join(lines))
        else:
            self.msg("You have not earned any achievements.")


class CmdAwardAchievement(Command):
    """Award an achievement to a player.

    Usage:
        awardach <player> <achievement>

    Example:
        awardach Bob first_blood
    """

    key = "awardach"
    locks = "cmd:perm(Builder)"
    help_category = "Building"

    def func(self):
        if not self.args:
            self.msg("Usage: awardach <player> <achievement>")
            return
        parts = self.args.split(None, 1)
        if len(parts) < 2:
            self.msg("Usage: awardach <player> <achievement>")
            return
        player_name, ach_key = parts
        ach_key = normalize_achievement_key(ach_key)
        idx, ach = AchievementManager.find(ach_key)
        if not ach:
            self.msg("Unknown achievement.")
            return
        target = self.caller.search_first(player_name, global_search=True)
        if not target:
            return
        earned = target.db.achievements or []
        if ach_key in earned:
            self.msg(f"{target.key} already has that achievement.")
            return
        earned.append(ach_key)
        target.db.achievements = earned
        title = ach.title or ach_key
        announce = ach.award_msg or f"You have earned the achievement '{title}'!"
        target.msg(announce)
        self.msg(f"{target.key} awarded '{title}'.")


class AchievementCmdSet(CmdSet):
    key = "Achievement CmdSet"

    def at_cmdset_creation(self):
        super().at_cmdset_creation()
        self.add(CmdAchievements)
        self.add(CmdAwardAchievement)
