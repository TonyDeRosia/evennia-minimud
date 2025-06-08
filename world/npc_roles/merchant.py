"""Merchant role mixin."""

class MerchantRole:
    """Mixin providing simple merchant behavior."""

    def sell(self, buyer, item, price: int) -> None:
        """Handle selling `item` to `buyer`."""
        if not buyer or not item:
            return
        buyer.msg(f"{self.key} sells {item} to you for {price} coins.")
