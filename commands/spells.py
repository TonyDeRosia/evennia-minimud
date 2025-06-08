from evennia import CmdSet
from evennia.utils.evtable import EvTable
from .command import Command
from world.spells import SPELLS


class CmdSpellbook(Command):
    """View known spells."""
    key = "spells"
    aliases = ("spellbook",)

    def func(self):
        known = self.caller.db.spells or []
        if not known:
            self.msg("You do not know any spells.")
            return
        table = EvTable("Spell", "Mana")
        for skey in known:
            spell = SPELLS.get(skey)
            if spell:
                table.add_row(spell.key, spell.mana_cost)
        self.msg(str(table))


class CmdCast(Command):
    """Cast a learned spell."""
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
        if spell_key not in known:
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
        if spell_key in known:
            self.msg("You already know that spell.")
            return
        known.append(spell_key)
        self.caller.db.spells = known
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

