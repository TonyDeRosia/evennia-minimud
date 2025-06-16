from evennia import CmdSet
from .command import Command
from world.system.class_skills import get_class_skills
from world.system import state_manager


class CmdUpdate(Command):
    """Update a character's skills based on their class and level."""

    key = "update"
    locks = "cmd:perm(Admin)"
    help_category = "Admin"

    def func(self):
        caller = self.caller
        if not self.args:
            caller.msg("Usage: update <target>")
            return
        target = caller.search(self.args.strip(), global_search=True)
        if not target:
            return
        charclass = target.db.charclass
        level = target.db.level
        if not charclass or level is None:
            caller.msg(f"{target.key} lacks a class or level.")
            return
        existing = set(target.db.skills or [])
        learned = []
        for skill in get_class_skills(charclass, level):
            if skill not in existing:
                learned.append(skill)
            state_manager.grant_ability(target, skill)
        if learned:
            caller.msg(f"{target.key} learns: {', '.join(learned)}")
        else:
            caller.msg(f"{target.key} already knows all appropriate skills.")


class UpdateCmdSet(CmdSet):
    key = "Update CmdSet"

    def at_cmdset_creation(self):
        super().at_cmdset_creation()
        self.add(CmdUpdate)
