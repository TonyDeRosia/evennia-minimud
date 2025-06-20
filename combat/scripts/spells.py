"""Helpers for casting spells in and out of combat."""

from __future__ import annotations

from typing import Optional

from world.skills.utils import maybe_start_combat

from ..combat_actions import SpellAction
from combat.spells import SPELLS, Spell


def get_spell(key: str) -> Optional[Spell]:
    """Return the spell matching ``key``."""
    return SPELLS.get(key)


def queue_spell(
    caster: object,
    spell: str | Spell,
    target: Optional[object] = None,
    *,
    engine: Optional[object] = None,
    start_combat: bool = False,
):
    """Queue ``spell`` on ``engine`` or resolve immediately."""
    if isinstance(spell, Spell):
        key = spell.key
    else:
        key = spell
        spell = get_spell(key)
    if not spell:
        return None
    if start_combat and target:
        maybe_start_combat(caster, target)
    if engine is None and hasattr(caster, "ndb"):
        engine = getattr(caster.ndb, "combat_engine", None)
    if engine:
        engine.queue_action(caster, SpellAction(caster, key, target))
        return None
    cast = getattr(caster, "cast_spell", None)
    if callable(cast):
        cast(key, target)
        return None
    action = SpellAction(caster, key, target)
    return action.resolve()


def resolve_spell(caster: object, spell: str | Spell, target: Optional[object] = None):
    """Resolve ``spell`` immediately."""
    return queue_spell(caster, spell, target, engine=None)
