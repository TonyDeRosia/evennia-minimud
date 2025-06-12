"""Combat-related helper functions for the world package."""

from combat import combat_utils

__all__ = ["get_health_description"]


def get_health_description(char):
    """Return a health status string for `char`.

    This looks for ``traits.health`` on ``char`` if available, with
    ``char.hp`` and ``char.max_hp`` as fallbacks. The values are then
    passed to :func:`combat.combat_utils.get_condition_msg` to create a
    readable description.
    """
    hp_trait = getattr(getattr(char, "traits", None), "health", None)
    cur = getattr(hp_trait, "value", getattr(char, "hp", 0))
    max_hp = getattr(hp_trait, "max", getattr(char, "max_hp", cur))
    return combat_utils.get_condition_msg(cur, max_hp)
