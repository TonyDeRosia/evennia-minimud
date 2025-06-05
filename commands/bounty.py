from evennia import CmdSet
from .command import Command


class CmdBounty(Command):
    """Set a bounty on a target."""

    key = "bounty"
    help_category = "general"

    def parse(self):
        self.target_name, self.amount = None, None
        if '=' in self.args:
            lhs, rhs = self.args.split('=', 1)
            self.target_name = lhs.strip()
            self.amount = rhs.strip()
        else:
            parts = self.args.split()
            if len(parts) >= 2:
                self.target_name = parts[0]
                self.amount = parts[1]

    def func(self):
        if not self.target_name or not self.amount:
            self.msg("Usage: bounty <target>=<amount>")
            return
        target = self.caller.search(self.target_name)
        if not target:
            return
        try:
            amount = int(self.amount)
        except ValueError:
            self.msg("Amount must be a number.")
            return
        if amount <= 0:
            self.msg("Amount must be positive.")
            return
        coins = self.caller.db.coins or 0
        if coins < amount:
            self.msg("You don't have that many coins.")
            return
        self.caller.db.coins = coins - amount
        target.db.bounty = (target.db.bounty or 0) + amount
        self.msg(f"You placed a {amount} coin bounty on {target.key}.")
        target.msg(f"A bounty of {amount} coins has been placed on you!")


class BountyCmdSet(CmdSet):
    key = "Bounty CmdSet"

    def at_cmdset_creation(self):
        super().at_cmdset_creation()
        self.add(CmdBounty)
