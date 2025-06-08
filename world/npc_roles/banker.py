"""Banker role mixin."""

class BankerRole:
    """Mixin providing simple banker behavior."""

    def deposit(self, depositor, amount: int) -> None:
        """Handle depositing currency from `depositor`."""
        if not depositor:
            return
        depositor.msg(f"You deposit {amount} coins with {self.key}.")

    def withdraw(self, withdrawer, amount: int) -> None:
        """Handle withdrawing currency for `withdrawer`."""
        if not withdrawer:
            return
        withdrawer.msg(f"{self.key} gives you {amount} coins from your account.")
