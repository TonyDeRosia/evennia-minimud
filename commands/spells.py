from evennia import CmdSet
from evennia.utils.evtable import EvTable
from .command import Command
from world.spells import SPELLS, Spell


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
                    spell = SPELLS.get(spell_key)
                    if not spell:
                        continue
                    prof = (
                        0
                        if isinstance(entry, str)
                        else getattr(entry, "proficiency", 0)
                    )
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
                spell = SPELLS.get(entry)
                if not spell:
                    continue
                prof = 0
                key = entry
            else:
                spell = SPELLS.get(entry.key)
                key = entry.key
                prof = getattr(entry, "proficiency", 0)
            if spell:
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
        spell = SPELLS.get(spell_key)
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
        self.caller.traits.mana.current -= spell.mana_cost
        if target:
            self.caller.location.msg_contents(
                f"{self.caller.get_display_name(self.caller)} casts {spell.key} at {target.get_display_name(self.caller)}!"
            )
        else:
            self.caller.location.msg_contents(
                f"{self.caller.get_display_name(self.caller)} casts {spell.key}!"
            )
        if isinstance(spell_entry, Spell):
            if spell_entry.proficiency < 100:
                spell_entry.proficiency = min(100, spell_entry.proficiency + 1)
            self.caller.db.spells = known


class CmdLearnSpell(Command):
    """Learn a spell from a trainer."""

    key = "learn"

    def func(self):
        if not self.obj or not (spell_key := self.obj.db.spell_training):
            self.msg("You cannot learn spells here.")
            return
        spell = SPELLS.get(spell_key)
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
        from world.system import proficiency_manager

        if (self.caller.db.practice_sessions or 0) <= 0:
            self.msg("You have no practice sessions left.")
            return
        new_spell = Spell(spell.key, spell.stat, spell.mana_cost, spell.desc, 0)
        spent, prof = proficiency_manager.practice(self.caller, new_spell)
        if spent:
            known.append(new_spell)
            self.caller.db.spells = known
            self.msg(f"You learn the {spell.key} spell.")
        else:
            self.msg("You have no practice sessions left.")


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
