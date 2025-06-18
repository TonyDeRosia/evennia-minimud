"""Utility helpers for casting spells and using skills."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def cast_spell(caster, spell_key: str, target=None):
    """Attempt to cast ``spell_key`` using ``caster``."""
    cast_fn = getattr(caster, "cast_spell", None)
    if callable(cast_fn):
        return cast_fn(spell_key, target=target)
    logger.debug("%s has no cast_spell method", caster)
    return False


def use_skill(user, skill_name: str, target=None):
    """Attempt to use ``skill_name`` for ``user``."""
    use_fn = getattr(user, "use_skill", None)
    if callable(use_fn):
        return use_fn(skill_name, target=target)
    logger.debug("%s has no use_skill method", user)
    return None
