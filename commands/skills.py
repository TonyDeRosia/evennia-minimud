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
        self.msg(f"EXP: {caller.db.exp or 0}")

        # display the primary stats
        self.msg("STATS")
        stats = []
        for key in CORE_STAT_KEYS:
            trait = caller.traits.get(key)
            value = trait.value if trait else 0
            stats.append([key, value])
        if (per := caller.traits.get("perception")):
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
    Improve a skill, based on how much experience you have.

    Enter just "train" by itself to see what you can learn here.

    Usage:
        train <levels>

    Example:
        train 5
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
            self.msg("Usage: train <levels>")
            return

        can_train, cost = self.obj.check_training(caller, levels)
        if can_train is None:
            self.msg("You cannot train any skills here.")
            return
        if can_train is False:
            self.msg(
                f"You do not have enough experience - you need {cost} experience to increase your {to_train} by {levels} levels."
            )
            return

        confirm = yield (
            f"It will cost you {cost} experience to improve your {to_train} by {levels} levels. Confirm? Yes/No"
        )
        if confirm.lower() not in ("yes", "y"):
            self.msg("Cancelled.")
            return

        success, spent, new_level = self.obj.train_skill(caller, levels)
        if not success:
            self.msg(
                f"You do not have enough experience - you need {spent} experience to improve your {to_train}."
            )
            return

        self.msg(f"You practice your {to_train} and improve it to level {new_level}.")


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
