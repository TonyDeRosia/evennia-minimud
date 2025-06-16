from .roles import has_role, is_guildmaster, is_receptionist


from .slots import VALID_SLOTS, normalize_slot
from .ansi_utils import format_ansi_title
from .menu_utils import add_back_skip
try:  # optional during early initialization
    from .mob_utils import (
        assign_next_vnum,
        add_to_mlist,
        auto_calc,
        auto_calc_secondary,
        make_corpse,
    )
except Exception:  # pragma: no cover - may fail before Django setup
    pass
try:
    from .eval_utils import eval_safe
except Exception:  # pragma: no cover - may fail before Django setup
    def eval_safe(*args, **kwargs):
        raise RuntimeError("eval_safe unavailable before Django setup")

from .dice import roll_dice_string
from .defense_scaling import DefensiveStats


def display_auto_prompt(account, caller, msg_func, *, force=False):
    """Display ``caller``'s status prompt if enabled on ``account``.

    Args:
        account (Account): The account storing the settings.
        caller (Object): The character whose status should be displayed.
        msg_func (callable): Function used to send the prompt.
        force (bool, optional): If ``True``, always send the prompt
            regardless of account settings. Defaults to ``False``.
    """

    if force or (account and (settings := account.db.settings) and settings.get("auto prompt")):
        status = caller.get_display_status(caller)
        msg_func(prompt=status)


import re

def auto_search(caller, search, **kwargs):
    """Search quietly and auto-select the first visible/living match."""
    results = caller.search(search, quiet=True, **kwargs)
    if not results:
        return None
    if not isinstance(results, list):
        return results
    if len(results) == 1:
        return results[0]
    # ignore auto-selection when specifying a numbered alias
    if re.match(r"^\d+-", search.strip()):
        return results[0]
    visible = [obj for obj in results if getattr(caller, "can_see", lambda o: True)(obj)]
    living = [obj for obj in visible if not (hasattr(obj, "tags") and obj.tags.has("unconscious", category="status"))]
    matches = living or visible or results
    matches.sort(key=lambda o: getattr(o, "id", 0))
    return matches[0]
