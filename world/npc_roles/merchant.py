"""Merchant role mixin."""

class MerchantRole:
    """Mixin providing simple merchant behavior."""

    def sell(self, buyer, item, price: int) -> None:
        """Sell ``item`` to ``buyer`` and exchange coins."""
        if not buyer or not item:
            return

        from utils.currency import to_copper, from_copper

        wallet = buyer.db.coins or {}
        if to_copper(wallet) < price:
            buyer.msg("You cannot afford that.")
            return

        item.move_to(buyer, quiet=True, move_type="get")

        buyer.db.coins = from_copper(to_copper(wallet) - price)
        my_wallet = self.db.coins or {}
        self.db.coins = from_copper(to_copper(my_wallet) + price)

        buyer.msg(f"{self.key} sells {item.get_display_name(buyer)} to you for {price} coins.")
