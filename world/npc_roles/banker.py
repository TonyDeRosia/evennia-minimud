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

    def balance(self, player) -> None:
        """Report ``player``'s wallet and bank balance."""
        if not player:
            return

        from utils.currency import format_wallet

        wallet = player.db.coins or {}
        bank = int(player.db.bank or 0)
        player.msg(
            f"You have {format_wallet(wallet)} on hand and {bank} coins in the bank."
        )

    def transfer(self, sender, receiver, amount: int) -> None:
        """Move ``amount`` coins from ``sender`` to ``receiver``'s bank accounts."""
        if not sender or not receiver or amount <= 0:
            return

        balance = int(sender.db.bank or 0)
        if balance < amount:
            sender.msg("You do not have that much saved.")
            return

        sender.db.bank = balance - amount
        receiver.db.bank = int(receiver.db.bank or 0) + amount

        sender.msg(
            f"You transfer {amount} coins to {receiver.get_display_name(sender)} through {self.key}."
        )
        if receiver != sender:
            receiver.msg(
                f"{self.key} transfers {amount} coins to your account from {sender.get_display_name(receiver)}."
            )
