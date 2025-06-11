"""Banker role mixin."""

class BankerRole:
    """Mixin providing simple banker behavior."""

    def deposit(self, depositor, amount: int) -> None:
        """Deposit ``amount`` of coins from ``depositor`` into their bank."""
        if not depositor or amount <= 0:
            return

        from utils.currency import deposit_coins

        if not deposit_coins(depositor, amount):
            depositor.msg("You don't have that much coin.")
            return

        depositor.msg(f"You deposit {amount} coins with {self.key}.")

    def withdraw(self, withdrawer, amount: int) -> None:
        """Withdraw ``amount`` of coins for ``withdrawer`` from their bank."""
        if not withdrawer or amount <= 0:
            return

        from utils.currency import withdraw_coins

        if not withdraw_coins(withdrawer, amount):
            withdrawer.msg("You do not have that much saved.")
            return

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

        from utils.currency import transfer_coins

        if not transfer_coins(sender, receiver, amount):
            sender.msg("You do not have that much saved.")
            return

        sender.msg(
            f"You transfer {amount} coins to {receiver.get_display_name(sender)} through {self.key}."
        )
        if receiver != sender:
            receiver.msg(
                f"{self.key} transfers {amount} coins to your account from {sender.get_display_name(receiver)}."
            )
