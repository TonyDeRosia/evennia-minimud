from evennia import CmdSet
from evennia.utils.evtable import EvTable

from .command import Command
from world.skills.kick import Kick
from world.skills.utils import maybe_start_combat
from combat.combat_actions import SkillAction
from world.system import state_manager


class CmdSkills(Command):
    """Display known skills and current proficiency."""

    key = "skills"

    def func(self):
        caller = self.caller
        known = caller.db.skills or []
        if not known:
            caller.msg("|rYou do not know any skills.|n")
            return

        table = EvTable("Skill", "Proficiency")
        profs = caller.db.proficiencies or {}
        for skill in sorted(known):
            table.add_row(skill, f"{profs.get(skill, 0)}%")

        caller.msg(str(table))


class CmdKick(Command):
    """Kick an opponent to start combat."""

    key = "kick"
    help_category = "Combat"

    def func(self):
        if not self.args:
            self.msg("Kick whom?")
            return
        target = self.caller.search(self.args.strip())
        if not target:
            return
        skill = Kick()
        if not self.caller.cooldowns.ready(skill.name):
            self.msg("You are still recovering.")
            return
        if self.caller.traits.stamina.current < skill.stamina_cost:
            self.msg("You are too exhausted.")
            return
        state_manager.add_cooldown(self.caller, skill.name, skill.cooldown)
        inst = maybe_start_combat(self.caller, target)
        inst.engine.queue_action(self.caller, SkillAction(self.caller, skill, target))


class AbilityCmdSet(CmdSet):
    key = "Ability CmdSet"

    def at_cmdset_creation(self):
        super().at_cmdset_creation()
        self.add(CmdSkills)
        self.add(CmdKick)
