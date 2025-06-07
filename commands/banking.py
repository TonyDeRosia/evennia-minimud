from evennia import CmdSet
from utils.currency import COIN_VALUES, format_wallet
from commands.command import Command


class CmdDeposit(Command):
    """Deposit coins into your bank account."""

    key = "deposit"
    help_category = "Here"

    def func(self):
        if not self.args:
            self.msg("Usage: deposit <amount> <coin>")
            return
        parts = self.args.split()
        if len(parts) != 2 or not parts[0].isdigit() or parts[1].lower() not in COIN_VALUES:
            self.msg("Usage: deposit <amount> <coin>")
            return
        amount = int(parts[0])
        ctype = parts[1].lower()
        wallet = self.caller.db.coins or {}
        if amount <= 0 or wallet.get(ctype, 0) < amount:
            self.msg("You don't have that many coins.")
            return
        wallet[ctype] = wallet.get(ctype, 0) - amount
        self.caller.db.coins = wallet
        bank = self.caller.db.bank or {}
        bank[ctype] = int(bank.get(ctype, 0)) + amount
        self.caller.db.bank = bank
        self.msg(f"You deposit {amount} {ctype} coin{'s' if amount != 1 else ''}.")


class CmdWithdraw(Command):
    """Withdraw coins from your bank account."""

    key = "withdraw"
    help_category = "Here"

    def func(self):
        if not self.args:
            self.msg("Usage: withdraw <amount> <coin>")
            return
        parts = self.args.split()
        if len(parts) != 2 or not parts[0].isdigit() or parts[1].lower() not in COIN_VALUES:
            self.msg("Usage: withdraw <amount> <coin>")
            return
        amount = int(parts[0])
        ctype = parts[1].lower()
        bank = self.caller.db.bank or {}
        if amount <= 0 or bank.get(ctype, 0) < amount:
            self.msg("You don't have that much stored.")
            return
        bank[ctype] = bank.get(ctype, 0) - amount
        self.caller.db.bank = bank
        wallet = self.caller.db.coins or {}
        wallet[ctype] = int(wallet.get(ctype, 0)) + amount
        self.caller.db.coins = wallet
        self.msg(f"You withdraw {amount} {ctype} coin{'s' if amount != 1 else ''}.")


class CmdBank(Command):
    """Show your bank balance."""

    key = "bank"
    help_category = "Here"

    def func(self):
        funds = self.caller.db.bank or {}
        self.msg(f"You have {format_wallet(funds)} stored in the bank.")


class BankCmdSet(CmdSet):
    """Command set for banker NPCs."""

    key = "Bank CmdSet"

    def at_cmdset_creation(self):
        super().at_cmdset_creation()
        self.add(CmdDeposit)
        self.add(CmdWithdraw)
        self.add(CmdBank)
