"""Simple helpers for working with coins."""

# Value of each coin type in copper pieces. One silver is worth 10 copper,
# one gold is worth 10 silver (100 copper) and one platinum is worth
# 10 gold (1000 copper).
COIN_VALUES = {
    "copper": 1,
    "silver": 10,
    "gold": 100,
    "platinum": 1000,
}


def to_copper(wallet) -> int:
    """Convert a wallet to its total value in copper.

    The wallet is a mapping of coin names to amounts using the ratios in
    :data:`COIN_VALUES` (1 silver = 10 copper, 1 gold = 100 copper,
    1 platinum = 1000 copper).
    """
    if wallet is None:
        return 0
    if isinstance(wallet, int):
        return wallet
    total = 0
    for coin, value in COIN_VALUES.items():
        total += value * int(wallet.get(coin, 0))
    return total


def from_copper(amount: int) -> dict:
    """Break down a copper amount into coin denominations.

    Uses :data:`COIN_VALUES` to determine how many platinum, gold, silver
    and copper pieces make up the given ``amount``.
    """
    remaining = int(amount)
    wallet = {}
    for coin, value in sorted(COIN_VALUES.items(), key=lambda kv: kv[1], reverse=True):
        wallet[coin], remaining = divmod(remaining, value)
    return wallet


def format_wallet(wallet, *, show_zero: bool = False) -> str:
    """Return a human-readable currency string.

    Args:
        wallet: Mapping of coin names to amounts or an integer copper value.
        show_zero: When ``True``, include zero-valued denominations between the
            highest and lowest non-zero coins.
    """
    if wallet is None:
        wallet = {}
    if isinstance(wallet, int):
        wallet = from_copper(wallet)

    coins = ["platinum", "gold", "silver", "copper"]
    counts = [int(wallet.get(c, 0)) for c in coins]

    if not any(counts):
        return "0 Copper"

    if not show_zero:
        parts = [
            f"{count} {coin.capitalize()}"
            for coin, count in zip(coins, counts)
            if count
        ]
        return ", ".join(parts)

    # determine range from highest to lowest non-zero denomination
    first = next(i for i, c in enumerate(counts) if c)
    last = len(coins) - 1 - next(i for i, c in enumerate(reversed(counts)) if c)

    parts = [
        f"{counts[i]} {coins[i].capitalize()}"
        for i in range(first, last + 1)
    ]
    return ", ".join(parts)


def deposit_coins(character, amount: int) -> bool:
    """Deposit ``amount`` of coins from ``character``'s wallet into their bank.

    Returns ``True`` if the transaction succeeded, ``False`` otherwise.
    """
    if not character or amount <= 0:
        return False

    wallet = character.db.coins or {}
    if to_copper(wallet) < amount:
        return False

    character.db.coins = from_copper(to_copper(wallet) - amount)
    character.db.bank = int(character.db.bank or 0) + amount
    return True


def withdraw_coins(character, amount: int) -> bool:
    """Withdraw ``amount`` of coins from ``character``'s bank into their wallet.

    Returns ``True`` if the transaction succeeded, ``False`` otherwise.
    """
    if not character or amount <= 0:
        return False

    balance = int(character.db.bank or 0)
    if balance < amount:
        return False

    character.db.bank = balance - amount
    wallet = character.db.coins or {}
    character.db.coins = from_copper(to_copper(wallet) + amount)
    return True


def transfer_coins(sender, receiver, amount: int) -> bool:
    """Transfer ``amount`` coins from ``sender``'s bank to ``receiver``'s bank.

    Returns ``True`` if the transaction succeeded, ``False`` otherwise.
    """
    if not sender or not receiver or amount <= 0:
        return False

    balance = int(sender.db.bank or 0)
    if balance < amount:
        return False

    sender.db.bank = balance - amount
    receiver.db.bank = int(receiver.db.bank or 0) + amount
    return True


