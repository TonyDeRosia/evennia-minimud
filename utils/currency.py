COIN_VALUES = {
    "copper": 1,
    "silver": 10,
    "gold": 100,
    "platinum": 1000,
}


def to_copper(wallet) -> int:
    """Convert a wallet to a value in copper."""
    if wallet is None:
        return 0
    if isinstance(wallet, int):
        return wallet
    total = 0
    for coin, value in COIN_VALUES.items():
        total += value * int(wallet.get(coin, 0))
    return total


def from_copper(amount: int) -> dict:
    """Convert an amount of copper to a wallet dict."""
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


