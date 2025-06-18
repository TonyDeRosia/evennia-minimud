# Helper functions for skill and spell use
from __future__ import annotations

from collections.abc import Mapping
from combat.combat_actions import CombatResult
from combat.combat_skills import SKILL_CLASSES
from world.spells import SPELLS, Spell
from world.system import state_manager


def use_skill(chara, skill_name: str, *args, **kwargs):
    """Use a skill either actively or passively."""
    target = kwargs.get("target")

    if target is not None:
        skill_cls = SKILL_CLASSES.get(skill_name)
        if not skill_cls:
            return CombatResult(actor=chara, target=target, message="Nothing happens.")
        skill = skill_cls()
        if not chara.cooldowns.ready(skill.name):
            return CombatResult(actor=chara, target=chara, message="Still recovering.")
        if chara.traits.stamina.current < skill.stamina_cost:
            return CombatResult(actor=chara, target=chara, message="Too exhausted.")
        chara.traits.stamina.current -= skill.stamina_cost
        state_manager.add_cooldown(chara, skill.name, skill.cooldown)
        result = skill.resolve(chara, target)
        for eff in getattr(skill, "effects", []):
            state_manager.add_status_effect(target, eff.key, eff.duration)
        return result

    if not skill_name:
        return 1
    skill_trait = chara.traits.get(skill_name)
    if not skill_trait:
        return 0

    stat_bonus = 0
    if stat := getattr(skill_trait, "stat", None):
        stat_bonus = state_manager.get_effective_stat(chara, stat)
    prof = getattr(skill_trait, "proficiency", 0)
    if prof < 100:
        skill_trait.proficiency = min(100, prof + 1)
    return skill_trait.value + stat_bonus


def cast_spell(caster, spell_key: str, target=None):
    """Cast a spell and return a combat result."""
    spell = SPELLS.get(spell_key)
    if not spell:
        return CombatResult(actor=caster, target=target or caster, message="Nothing happens.")
    if not caster.cooldowns.ready(spell.key):
        return CombatResult(actor=caster, target=caster, message="Still recovering.")

    known = caster.db.spells or []
    if isinstance(known, Mapping):
        known = list(known.keys())
        caster.db.spells = known

    srec = None
    for entry in known:
        if isinstance(entry, str) and entry == spell_key:
            srec = Spell(spell.key, spell.stat, spell.mana_cost, spell.desc, 0)
            idx = known.index(entry)
            known[idx] = srec
            caster.db.spells = known
            break
        if hasattr(entry, "key") and entry.key == spell_key:
            srec = entry
            break
    if not srec:
        return CombatResult(actor=caster, target=caster, message="Nothing happens.")
    if caster.traits.mana.current < spell.mana_cost:
        return CombatResult(actor=caster, target=caster, message="Too exhausted.")

    caster.traits.mana.current -= spell.mana_cost
    state_manager.add_cooldown(caster, spell.key, spell.cooldown)

    if target:
        caster.location.msg_contents(
            f"{caster.get_display_name(caster)} casts {spell.key} at {target.get_display_name(caster)}!"
        )
        msg = f"{caster.key} casts {spell.key} at {target.key}!"
    else:
        caster.location.msg_contents(
            f"{caster.get_display_name(caster)} casts {spell.key}!"
        )
        msg = f"{caster.key} casts {spell.key}!"

    if srec.proficiency < 100:
        srec.proficiency = min(100, srec.proficiency + 1)
        caster.db.spells = known

    return CombatResult(actor=caster, target=target or caster, message=msg)

