"""Experience point utilities."""


def gain_xp(character, amount: int) -> None:
    """Award ``amount`` of experience to ``character``.

    Parameters
    ----------
    character
        The recipient of the experience points.
    amount
        How many points to award.
    """
    if not character or not amount:
        return
    try:
        amount = int(amount)
    except (TypeError, ValueError):
        return

    character.db.exp = (character.db.exp or 0) + amount
    if hasattr(character, "msg"):
        character.msg(f"You gain {amount} experience points!")

