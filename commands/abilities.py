from evennia import CmdSet
from evennia.utils.evtable import EvTable

from .command import Command
from world.skills.kick import Kick
from world.skills.utils import maybe_start_combat
from combat.combat_actions import SkillAction
from world.system import state_manager


class CmdSkills(Command):
    """List known skills and proficiency."""

    key = "skills"

    def func(self):
        known = self.caller.db.skills or []
        if not known:
            self.msg("You do not know any skills.")
            return
        table = EvTable("Skill", "Proficiency")
        profs = self.caller.db.proficiencies or {}
        for sk in known:
            table.add_row(sk, f"{profs.get(sk, 0)}%")
        self.msg(str(table))


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
        self.caller.traits.stamina.current -= skill.stamina_cost
        state_manager.add_cooldown(self.caller, skill.name, skill.cooldown)
        inst = maybe_start_combat(self.caller, target)
        inst.engine.queue_action(self.caller, SkillAction(self.caller, skill, target))


class AbilityCmdSet(CmdSet):
    key = "Ability CmdSet"

    def at_cmdset_creation(self):
        super().at_cmdset_creation()
        self.add(CmdSkills)
        self.add(CmdKick)
