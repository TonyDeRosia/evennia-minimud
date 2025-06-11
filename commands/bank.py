"""Banking command for managing stored coins.

Usage:
    bank balance
    bank deposit <amount [coin]>
    bank withdraw <amount [coin]>
    bank transfer <amount [coin]> <target>

Example:
    bank deposit 10 gold
"""

from .command import Command
from utils.currency import (
    COIN_VALUES,
    format_wallet,
    deposit_coins,
    withdraw_coins,
    transfer_coins,
)


class CmdBank(Command):
    """Handle deposits, withdrawals and transfers.

    Usage:
        bank <balance|deposit|withdraw|transfer>

    Example:
        bank transfer 50 silver bob
    """

    key = "bank"
    help_category = "General"

    def func(self):
        caller = self.caller
        if not self.args:
            caller.msg("Usage: bank <balance|deposit|withdraw|transfer>")
            return

        parts = self.args.split(None, 1)
        sub = parts[0].lower()
        rest = parts[1].strip() if len(parts) > 1 else ""

        if sub == "balance":
            wallet = caller.db.coins or {}
            bank = int(caller.db.bank or 0)
            caller.msg(
                f"You have {format_wallet(wallet)} on hand and {bank} coins in the bank."
            )
            return

        if sub in ("deposit", "withdraw"):
            if not rest:
                caller.msg(f"Usage: bank {sub} <amount [coin]>")
                return
            amount_parts = rest.split()
            if not amount_parts[0].isdigit():
                caller.msg(f"Usage: bank {sub} <amount [coin]>")
                return
            amt = int(amount_parts[0])
            coin = amount_parts[1].lower() if len(amount_parts) > 1 else "copper"
            if coin not in COIN_VALUES:
                caller.msg(f"Unknown coin type: {coin}.")
                return
            amount = amt * COIN_VALUES[coin]

            if sub == "deposit":
                if not deposit_coins(caller, amount):
                    caller.msg("You don't have that much coin.")
                    return
                caller.msg(f"You deposit {amount} coins into your account.")
            else:  # withdraw
                if not withdraw_coins(caller, amount):
                    caller.msg("You do not have that much saved.")
                    return
                caller.msg(f"You withdraw {amount} coins from your account.")
            return

        if sub == "transfer":
            if not rest:
                caller.msg("Usage: bank transfer <amount [coin]> <target>")
                return
            parts = rest.split(None, 2)
            if len(parts) < 2:
                caller.msg("Usage: bank transfer <amount [coin]> <target>")
                return
            if not parts[0].isdigit():
                caller.msg("Usage: bank transfer <amount [coin]> <target>")
                return
            amt = int(parts[0])
            if len(parts) == 2:
                coin = "copper"
                target_name = parts[1]
            else:
                coin = parts[1].lower()
                target_name = parts[2]
            if coin not in COIN_VALUES:
                caller.msg(f"Unknown coin type: {coin}.")
                return
            amount = amt * COIN_VALUES[coin]
            target = caller.search(target_name, global_search=True)
            if not target:
                return
            if not transfer_coins(caller, target, amount):
                caller.msg("You do not have that much saved.")
                return
            caller.msg(
                f"You transfer {amount} coins to {target.get_display_name(caller)}."
            )
            if target != caller:
                target.msg(
                    f"{caller.get_display_name(target)} transfers {amount} coins to your account."
                )
            return

        caller.msg("Usage: bank <balance|deposit|withdraw|transfer>")

