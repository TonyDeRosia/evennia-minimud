"""Dice rolling utilities."""

import random
import re

_DICE_TERM = re.compile(r"(?P<count>\d*)d(?P<sides>\d+)", re.I)


def roll_dice_string(formula: str) -> int:
    """Roll dice defined by ``formula``.

    The formula may contain dice expressions like ``'2d6'`` mixed with
    integer values separated by ``+`` or ``-``. Missing counts default
    to one die.
    """
    if not formula:
        return 0

    expr = str(formula).replace(" ", "")
    total = 0
    for term in re.finditer(r"([+-]?[^+-]+)", expr):
        piece = term.group(0)
        sign = 1
        if piece[0] in "+-":
            if piece[0] == "-":
                sign = -1
            piece = piece[1:]
        match = _DICE_TERM.fullmatch(piece)
        if match:
            count = int(match.group("count") or 1)
            sides = int(match.group("sides"))
            value = sum(random.randint(1, sides) for _ in range(count))
        else:
            value = int(piece)
        total += sign * value
    return total
