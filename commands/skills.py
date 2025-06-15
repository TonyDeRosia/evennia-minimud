from evennia import CmdSet
from evennia.utils.evtable import EvTable
from world.stats import CORE_STAT_KEYS
from .command import Command

# A dict of all skills, with their associated stat as the value
SKILL_DICT = {
    "smithing": "STR",
    "tailoring": "DEX",
    "evasion": "DEX",
    "daggers": "DEX",
    "swords": "STR",
    "cooking": "WIS",
    "carving": "STR",
    "slash": "STR",
    "kick": "STR",
    "unarmed": "DEX",
    "leatherwork": "WIS",
}


class CmdStatSheet(Command):
    """
    View your character's current stats and known skills.
    (aliases: "sheet", "skills")
    """

    key = "stats"
    aliases = ("sheet", "skills")

    def func(self):
        caller = self.caller

        self.msg(f"|w{caller.name}|n")
        # display current status
        self.msg(caller.get_display_status(caller))
        self.msg(f"EXP: {caller.db.experience or 0}")

        # display the primary stats
        self.msg("STATS")
        stats = []
        for key in CORE_STAT_KEYS:
            trait = caller.traits.get(key)
            value = trait.value if trait else 0
            stats.append([key, value])
        if per := caller.traits.get("perception"):
            stats.append(["PER", per.value])
        rows = list(zip(*stats))
        table = EvTable(table=rows, border="none")
        self.msg(str(table))

        # display known skills
        self.msg("SKILLS")
        skills = []
        for skill_key in sorted(SKILL_DICT.keys()):
            if skill := caller.traits.get(skill_key):
                skills.append((skill.name, int(skill.value)))
        rows = list(zip(*skills))
        if not rows:
            self.msg("(None)")
        table = EvTable(table=rows, border="none")
        self.msg(str(table))


class CmdTrainSkill(Command):
    """
    Spend practice sessions to improve a skill.

    Enter just "train" by itself to see what you can learn here.

    Usage:
        train <sessions>

    Example:
        train 2
    """

    key = "train"

    def func(self):
        if not self.obj:
            self.msg("You cannot train skills here.")
            return
        if not (to_train := self.obj.db.skill_training):
            self.msg("You cannot train any skills here.")
            return

        # make sure this is actually a valid skill
        if to_train not in SKILL_DICT:
            self.msg("You cannot train any skills here.")
            return

        if not self.args:
            self.msg(f"You can improve your |w{to_train}|n here.")
            return

        caller = self.caller

        try:
            levels = int(self.args.strip())
        except ValueError:
            self.msg("Usage: train <sessions>")
            return

        can_train, cost = self.obj.check_training(caller, levels)
        if can_train is None:
            self.msg("You cannot train any skills here.")
            return
        if can_train is False:
            self.msg("You do not have enough practice sessions.")
            return

        confirm = yield (
            f"Spend {levels} practice session{'s' if levels != 1 else ''} to improve your {to_train}? Yes/No"
        )
        if confirm.lower() not in ("yes", "y"):
            self.msg("Cancelled.")
            return

        success, spent, new_prof = self.obj.train_skill(caller, levels)
        if not success:
            self.msg("You do not have enough practice sessions.")
            return

        self.msg(f"You practice your {to_train} and reach {new_prof}% proficiency.")


class CmdTrainResource(Command):
    """Spend training points to raise max HP, MP or SP."""

    key = "trainres"

    def func(self):
        if not self.args or len(self.args.split()) != 2:
            self.msg("Usage: trainres <hp|mp|sp> <amount>")
            return

        stat_key, amt_str = self.args.split()
        stat_key = stat_key.lower()
        alias = {"hp": "health", "mp": "mana", "sp": "stamina"}
        if stat_key not in alias:
            self.msg("Specify hp, mp or sp.")
            return

        try:
            amount = int(amt_str)
        except ValueError:
            self.msg("Amount must be a number.")
            return

        if amount <= 0:
            self.msg("Amount must be positive.")
            return

        caller = self.caller
        points = caller.db.training_points or 0
        if points < amount:
            self.msg("You do not have enough training points.")
            return

        trait = caller.traits.get(alias[stat_key])
        trait.base += amount
        caller.db.training_points = points - amount

        from world.system import stat_manager

        stat_manager.refresh_stats(caller)

        self.msg(
            f"You spend {amount} training point{'s' if amount != 1 else ''} to increase your {trait.key}."
        )


class TrainCmdSet(CmdSet):
    key = "Train CmdSet"

    def at_cmdset_creation(self):
        super().at_cmdset_creation()
        self.add(CmdTrainSkill)


class SkillCmdSet(CmdSet):
    key = "Skill CmdSet"

    def at_cmdset_creation(self):
        super().at_cmdset_creation()
        self.add(CmdStatSheet)
        self.add(CmdTrainResource)
