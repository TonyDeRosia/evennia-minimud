from evennia import CmdSet
from evennia.utils.evtable import EvTable

from .command import Command
from world.system import proficiency_manager
from combat.combat_skills import SKILL_CLASSES
from combat.round_manager import CombatRoundManager
from combat.combat_actions import SkillAction
from world.abilities import ABILITY_REGISTRY
from .command import MuxCommand


def iter_skill_commands():
    """Yield dynamic MuxCommands for each registered skill ability."""
    for ability in ABILITY_REGISTRY.values():
        if getattr(ability, "class_type", "") != "skill":
            continue
        key = ability.name.lower()
        class_name = "Cmd" + "".join(part.capitalize() for part in key.split())

        def func(self, _skill=key):
            caller = self.caller
            if _skill not in (caller.db.skills or []):
                self.msg("You do not know that ability.")
                return
            target_name = self.args.strip()
            if target_name:
                target = caller.search(target_name)
                if not target:
                    return
            else:
                target = caller.db.combat_target
                if not target:
                    self.msg("Use it on whom?")
                    return
            result = caller.use_skill(_skill, target=target)
            if result and getattr(result, "message", None):
                caller.location.msg_contents(result.message)

        attrs = {"key": key, "help_category": "Combat", "func": func}
        yield type(class_name, (MuxCommand,), attrs)



class CmdSkills(Command):
    """List known combat abilities and their proficiency."""

    key = "skills"

    def func(self):
        caller = self.caller
        skills = caller.db.skills or []
        if not skills:
            self.msg("You do not know any abilities.")
            return
        table = EvTable("Ability", "Proficiency")
        for sk in skills:
            trait = caller.traits.get(sk)
            prof = getattr(trait, "proficiency", 0)
            table.add_row(sk, f"{prof}%")
        self.msg(str(table))


class CmdPractice(Command):
    """Spend one practice session to improve an ability."""

    key = "practice"

    def func(self):
        caller = self.caller
        if not self.args:
            self.msg("Practice what?")
            return
        ability = self.args.strip().lower()
        if ability not in (caller.db.skills or []):
            self.msg("You do not know that ability.")
            return
        trait = caller.traits.get(ability)
        if not trait:
            self.msg("You do not know that ability.")
            return
        spent, prof = proficiency_manager.practice(caller, trait)
        if not spent:
            self.msg("You have no practice sessions left.")
            return
        self.msg(f"You practice your {ability} and reach {prof}% proficiency.")


class CmdUse(Command):
    """Queue a combat ability to use."""

    key = "use"
    help_category = "Combat"

    def parse(self):
        args = self.args.strip()
        if " on " in args:
            self.skillname, self.targetname = args.split(" on ", 1)
        else:
            self.skillname = args
            self.targetname = None

    def func(self):
        caller = self.caller
        if not self.skillname:
            self.msg("Use what?")
            return
        skill_key = self.skillname.lower()
        if skill_key not in (caller.db.skills or []):
            self.msg("You do not know that ability.")
            return
        skill_cls = SKILL_CLASSES.get(skill_key)
        if not skill_cls:
            self.msg("You can't use that ability.")
            return
        skill = skill_cls()
        if not caller.cooldowns.ready(skill.name):
            self.msg("Still recovering.")
            return
        stamina = getattr(caller.traits, "stamina", None)
        if stamina and stamina.current < skill.stamina_cost:
            self.msg("You are too exhausted to do that.")
            return
        if self.targetname:
            target = caller.search(self.targetname)
            if not target:
                return
        else:
            target = caller.db.combat_target
            if not target:
                self.msg("Use it on whom?")
                return
        manager = CombatRoundManager.get()
        instance = manager.start_combat([caller, target])
        if caller not in instance.combatants:
            self.msg("You can't fight right now.")
            return
        instance.engine.queue_action(caller, SkillAction(caller, skill, target))
        self.msg(f"You prepare to use {skill.name} on {target.key}.")


class AbilityCmdSet(CmdSet):
    key = "Ability CmdSet"

    def at_cmdset_creation(self):
        super().at_cmdset_creation()
        self.add(CmdSkills)
        self.add(CmdPractice)
        self.add(CmdUse)
        for cmd in iter_skill_commands():
            self.add(cmd())
