"""Banker role mixin."""

class BankerRole:
    """Mixin providing simple banker behavior."""

    def deposit(self, depositor, amount: int) -> None:
        """Deposit ``amount`` of coins from ``depositor`` into their bank."""
        if not depositor or amount <= 0:
            return

        from utils.currency import to_copper, from_copper

        wallet = depositor.db.coins or {}
        if to_copper(wallet) < amount:
            depositor.msg("You don't have that much coin.")
            return

        depositor.db.coins = from_copper(to_copper(wallet) - amount)
        depositor.db.bank = int(depositor.db.bank or 0) + amount
        depositor.msg(f"You deposit {amount} coins with {self.key}.")

    def withdraw(self, withdrawer, amount: int) -> None:
        """Withdraw ``amount`` of coins for ``withdrawer`` from their bank."""
        if not withdrawer or amount <= 0:
            return

        from utils.currency import to_copper, from_copper

        balance = int(withdrawer.db.bank or 0)
        if balance < amount:
            withdrawer.msg("You do not have that much saved.")
            return

        withdrawer.db.bank = balance - amount
        wallet = withdrawer.db.coins or {}
        withdrawer.db.coins = from_copper(to_copper(wallet) + amount)
        withdrawer.msg(f"{self.key} gives you {amount} coins from your account.")
