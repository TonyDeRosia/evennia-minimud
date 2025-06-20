from evennia import CmdSet
from evennia.utils.evtable import EvTable

from .command import Command
from combat.scripts import queue_skill, get_skill
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
            if self.caller.in_combat and self.caller.db.combat_target:
                target = self.caller.db.combat_target
            else:
                self.msg("Kick whom?")
                return
        else:
            from utils import auto_search

            target = auto_search(self.caller, self.args.strip())
            if not target:
                return
        skill = get_skill("kick")
        if not skill:
            self.msg("Kick skill is unavailable.")
            return
        if state_manager.is_on_cooldown(self.caller, skill.name):
            self.msg("You are still recovering.")
            return
        if self.caller.traits.stamina.current < skill.stamina_cost:
            self.msg("You are too exhausted.")
            return
        # Apply costs and resolve via the combat script helper
        state_manager.add_cooldown(self.caller, skill.name, skill.cooldown)
        self.caller.traits.stamina.current -= skill.stamina_cost

        result = queue_skill(self.caller, skill, target, start_combat=True)
        if result and result.message and self.caller.location:
            self.caller.location.msg_contents(result.message, from_obj=self.caller)
        if result and result.damage:
            if hasattr(target, "at_damage"):
                target.at_damage(self.caller, result.damage, result.damage_type)
            elif hasattr(target, "hp"):
                target.hp = max(target.hp - result.damage, 0)


class AbilityCmdSet(CmdSet):
    key = "Ability CmdSet"

    def at_cmdset_creation(self):
        super().at_cmdset_creation()
        self.add(CmdSkills)
        self.add(CmdKick)
