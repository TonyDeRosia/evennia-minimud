"""Simple helpers for working with coins."""

# Value of each coin type in copper pieces. One silver is worth 100 copper,
# one gold is worth 10 silver (1000 copper) and one platinum is worth
# 100 gold (100000 copper).
COIN_VALUES = {
    "copper": 1,
    "silver": 100,
    "gold": 1000,
    "platinum": 100000,
}


def to_copper(wallet) -> int:
    """Convert a wallet to its total value in copper.

    The wallet is a mapping of coin names to amounts using the ratios in
    :data:`COIN_VALUES` (1 silver = 100 copper, 1 gold = 1000 copper,
    1 platinum = 100000 copper).
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


def format_wallet(wallet) -> str:
    """Return a human-readable currency string."""
    if wallet is None:
        wallet = {}
    if isinstance(wallet, int):
        wallet = from_copper(wallet)
    parts = []
    for coin in ["platinum", "gold", "silver", "copper"]:
        count = int(wallet.get(coin, 0))
        if count:
            parts.append(f"{count} {coin.capitalize()}")
    if not parts:
        return "0 Copper"
    return ", ".join(parts)


