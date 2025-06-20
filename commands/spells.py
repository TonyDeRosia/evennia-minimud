from evennia import CmdSet
from evennia.utils.evtable import EvTable
from .command import Command
from combat.scripts import get_spell, queue_spell
from world.spells import Spell, colorize_spell


class CmdSpellbook(Command):
    """View known spells or details about one spell.

    Usage:
        spells
        spells <spell>

    Example:
        spells fireball
    """

    key = "spells"
    aliases = ("spellbook",)

    def func(self):
        known = self.caller.db.spells or []
        if not known:
            self.msg("You do not know any spells.")
            return

        # if an argument was given, try to show details about that spell
        if self.args:
            spell_key = self.args.strip().lower()
            for entry in known:
                if (isinstance(entry, str) and entry == spell_key) or (
                    not isinstance(entry, str) and entry.key == spell_key
                ):
                    spell = get_spell(spell_key)
                    if not spell:
                        continue
                    profs = self.caller.db.proficiencies or {}
                    prof = profs.get(spell_key, 0)
                    msg = (
                        f"|w{spell.key.capitalize()}|n\n"
                        f"  Mana Cost: |w{spell.mana_cost}|n\n"
                        f"  Proficiency: |w{prof}%|n"
                    )
                    if spell.desc:
                        msg += f"\n  {spell.desc}"
                    self.msg(msg)
                    return
            self.msg("You have not learned that spell.")
            return

        table = EvTable("Spell", "Mana", "Proficiency")
        for entry in known:
                if isinstance(entry, str):
                    key = entry
                else:
                    key = entry.key
                spell = get_spell(key)
                if not spell:
                    continue
                profs = self.caller.db.proficiencies or {}
                prof = profs.get(key, 0)
                table.add_row(key, spell.mana_cost, f"{prof}%")
        self.msg(str(table))


class CmdCast(Command):
    """Cast a learned spell.

    Usage:
        cast <spell> [on <target>]

    Example:
        cast fireball on goblin
    """
    key = "cast"

    def parse(self):
        args = self.args.strip()
        if " on " in args:
            self.spellname, self.target = args.split(" on ", 1)
        else:
            self.spellname = args
            self.target = None

    def func(self):
        if not self.spellname:
            self.msg("Cast what?")
            return
        spell_key = self.spellname.lower()
        spell = get_spell(spell_key)
        if not spell:
            self.msg("No such spell.")
            return
        known = self.caller.db.spells or []
        spell_entry = None
        for entry in known:
            if (isinstance(entry, str) and entry == spell_key) or (
                not isinstance(entry, str) and entry.key == spell_key
            ):
                spell_entry = entry
                break
        if spell_entry is None:
            self.msg("You have not learned that spell.")
            return
        if self.caller.traits.mana.current < spell.mana_cost:
            self.msg("You do not have enough mana.")
            return
        target = None
        if self.target:
            target = self.caller.search(self.target)
            if not target:
                return
        result = queue_spell(self.caller, spell, target)
        if result and result.message and self.caller.location:
            self.caller.location.msg_contents(result.message)


class CmdLearnSpell(Command):
    """Learn a spell from a trainer."""
    key = "learn"

    def func(self):
        if not self.obj or not (spell_key := self.obj.db.spell_training):
            self.msg("You cannot learn spells here.")
            return
        spell = get_spell(spell_key)
        if not spell:
            self.msg("You cannot learn spells here.")
            return
        known = self.caller.db.spells or []
        for entry in known:
            if (isinstance(entry, str) and entry == spell_key) or (
                not isinstance(entry, str) and entry.key == spell_key
            ):
                self.msg("You already know that spell.")
                return
        if (self.caller.db.practice_sessions or 0) <= 0:
            self.msg("You have no practice sessions left.")
            return
        self.caller.db.practice_sessions -= 1
        new_spell = Spell(spell.key, spell.stat, spell.mana_cost, spell.desc, spell.cooldown)
        known.append(new_spell)
        self.caller.db.spells = known
        profs = self.caller.db.proficiencies or {}
        profs[spell.key] = 25
        self.caller.db.proficiencies = profs
        self.msg(f"You learn the {spell.key} spell.")


class SpellTrainCmdSet(CmdSet):
    key = "Spell Train CmdSet"

    def at_cmdset_creation(self):
        super().at_cmdset_creation()
        self.add(CmdLearnSpell)


class SpellCmdSet(CmdSet):
    key = "Spell CmdSet"

    def at_cmdset_creation(self):
        super().at_cmdset_creation()
        self.add(CmdSpellbook)
        self.add(CmdCast)

