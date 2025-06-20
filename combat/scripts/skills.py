"""Wrappers for using skills during combat."""

from __future__ import annotations

from typing import Optional, Union

from ..combat_actions import SkillAction
from ..skills import SKILL_CLASSES, Skill
from world.skills.utils import maybe_start_combat


def get_skill(name: str) -> Optional[Skill]:
    """Return a new instance of ``name`` if available."""
    cls = SKILL_CLASSES.get(name)
    return cls() if cls else None


def queue_skill(
    user: object,
    skill: Union[str, Skill],
    target: Optional[object] = None,
    *,
    engine: Optional[object] = None,
    start_combat: bool = False,
):
    """Queue ``skill`` on ``engine`` or resolve immediately."""
    if isinstance(skill, str):
        skill_obj = get_skill(skill)
    else:
        skill_obj = skill
    if not skill_obj:
        return None
    if start_combat and target:
        maybe_start_combat(user, target)
    if engine is None and hasattr(user, "ndb"):
        engine = getattr(user.ndb, "combat_engine", None)
    if engine:
        engine.queue_action(user, SkillAction(user, skill_obj, target))
        return None
    action = SkillAction(user, skill_obj, target)
    return action.resolve()


def resolve_skill(user: object, skill: Union[str, Skill], target: Optional[object] = None):
    """Resolve ``skill`` immediately."""
    return queue_skill(user, skill, target, engine=None)
