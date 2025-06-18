import random


def calculate_hit_success(chara, ability_key, support_skill=None):
    """Return True if ``chara`` succeeds with the given ability.

    Parameters
    ----------
    chara : object
        Character using the ability. Must have a ``db`` attribute.
    ability_key : str
        Key of the primary ability being attempted.
    support_skill : str, optional
        Name of a supporting skill providing a small bonus.
    """
    profs = getattr(getattr(chara, "db", None), "proficiencies", {}) or {}
    chance = profs.get(ability_key, 0)
    if support_skill:
        chance += profs.get(support_skill, 0) // 10
    return random.randint(1, 100) <= chance
